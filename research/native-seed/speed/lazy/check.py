#!/usr/bin/env python3
"""Native lazy differential (LAZY): compiled lazy BL in gsi against BEAM.

Usage: check.py MAIN-OUT LAZY-OUT
  MAIN-OUT  read-only research/native-seed/out of the integration checkout
            (speed-build/prelude.scm, speed-build/leaves.json)
  LAZY-OUT  directory holding lazy.scm (emit.bl) and oracle.scm (oracle.bl)

Builds LAZY-OUT/check.scm:
  1. this worktree's host sources in prepare-host.py order, with
     host/host-lazy.scm deleted and host/native-memo.scm appended;
  2. the natively emitted lazy namespaces (lazy.scm);
  3. the link step integration performs at emission time: every call site the
     closure emitted as a leaf of a lazy module is pointed at the compiled
     definition (`native-add-leaf!` on its cell); no lazy leaf exists before;
  4. the integration prelude's compiled closure (everything from its
     `native-install-bundle!` on), unchanged;
  5. the oracle rows, each evaluated by the native compiler
     (native.eval/eval-string) and compared with BEAM's outcome.
Runs it under the pinned gsi (timeout 120 s).
"""
import json
import re
import pathlib
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parents[2]
HOST = ["host.scm", "host/host-values.scm", "host/host-leaves.scm",
        "host/host-extra.scm", "host/host-compiler.scm", "host/host-match.scm", "host/host-kernel.scm",
        "host/native-memo.scm"]  # native-text.scm is FFI (gsc only), as in speed/kernel/gsi-run.py
# Leaves this check needs that other owners provide at integration; defined
# for this check only. `erlang/fun_info/2` gets one native leaf from the main
# thread; this stand-in answers `:arity` from the callable registry (the
# `:module` reads of fun literals are linked by emit.bl).
FOREIGN = r'''(native-add-leaf! "Elixir.BeamLisp.Tiers/priv_root/0" (lambda () "priv"))
(native-add-leaf! "erlang/fun_info/2"
 (lambda (f item)
  (if (and (eq? item (bl-key "arity")) (procedure? f) (pair? (table-ref native-callable-arities f '())))
   (bl-make-tuple item (car (table-ref native-callable-arities f '())))
   (error "harness fun_info: unsupported item" item))))
'''
MODULES = {"Elixir.BeamLisp.LazySeq": "host.lazy-seq", "Elixir.BeamLisp.SeqCursor": "host.seq-cursor",
           "Elixir.BeamLisp.Deferred": "host.deferred", "Elixir.BeamLisp.LazyMemo": "host.lazy-memo",
           "Elixir.BeamLisp.Delay": "host.delay", "Elixir.BeamLisp.LazySeq.ForceError": "host.lazy-seq-force-error"}

TO_FLOAT = r'''
;; native-text.scm's grapheme adapter needs ICU (gsc); ASCII stand-in here.
(set! native-graphemes (lambda (text) (map string (string->list text))))
(native-add-leaf! "string/to_float/1" (lambda (chars)
 (define (digits xs) (let loop ((xs xs) (n 0)) (if (and (pair? xs) (char-numeric? (integer->char (car xs)))) (loop (cdr xs) (+ n 1)) n)))
 (define (sign xs) (if (and (pair? xs) (memv (car xs) '(43 45))) 1 0))
 (let* ((s (sign chars)) (w (digits (list-tail chars s))) (at (+ s w))
        (frac (and (> w 0) (> (length chars) at) (= 46 (list-ref chars at)) (digits (list-tail chars (+ at 1))))))
  (if (not (and frac (> frac 0))) (bl-tuple (list (bl-key "error") (bl-key "no_float")))
   (let* ((end (+ at 1 frac))
          (e-end (if (and (> (length chars) end) (memv (list-ref chars end) '(69 101)))
                  (let* ((es (sign (list-tail chars (+ end 1)))) (ed (digits (list-tail chars (+ end 1 es)))))
                   (if (> ed 0) (+ end 1 es ed) end)) end))
          (prefix (list->string (map integer->char (native-take chars e-end)))))
    (bl-tuple (list (bl-float (exact->inexact (string->number prefix))) (list-tail chars e-end))))))))
'''

HARNESS = r'''
(define lazy-checks 0)
(define lazy-failures 0)
(define (lazy-native src)
 (with-exception-catcher
  (lambda (e) (list 'raised (let ((r (native-exception-reason e)))
                             (cond ((and (bl-tag? r 'map) (string? (bl-get r (bl-key "message") #f))) (bl-get r (bl-key "message")))
                                   ((string? r) r) (else (bl-show r))))))
  (lambda () (list 'ok (bl-invoke (native-global "native.eval" "eval-string") (list src "lazy-check"))))))
(define (lazy-case label src kind expected)
 (let ((got (lazy-native src)))
  (set! lazy-checks (+ lazy-checks 1))
  (if (not (and (eq? (car got) kind)
                (if (eq? kind 'ok) (bl-key-equal? (cadr got) expected) (equal? (cadr got) expected))))
   (begin (set! lazy-failures (+ lazy-failures 1))
    (display "LAZY_FAIL ") (display label) (display " ") (write (list 'beam kind expected 'native got)) (newline)))))
'''

def main(argv):
    main_out, lazy_out = pathlib.Path(argv[0]), pathlib.Path(argv[1])
    host = "\n".join((BASE / p).read_text() for p in HOST)
    # native-text.scm needs gsc (FFI); its leaves exist here as refusals,
    # except the reader's float scan, which gets the same grammar without PCRE.
    text_keys = re.findall(r'native-add-leaf! "([^"]+)"', (BASE / "host/native-text.scm").read_text())
    host += "\n" + "".join('(native-add-leaf! %s (native-unavailable %s))\n' % (json.dumps(k), json.dumps(k))
                           for k in text_keys if k != "string/to_float/1") + TO_FLOAT
    prelude = (main_out / "speed-build/prelude.scm").read_text()
    closure = prelude[prelude.index("\n(native-install-bundle! (bl-map") + 1:]
    leaves = json.loads((main_out / "speed-build/leaves.json").read_text())["registered_leaves"]
    relink = []
    for key in sorted(leaves):
        module, name, arity = key.rsplit("/", 2)
        if module in MODULES:
            relink.append('(lazy-relink! %s %s %s %s)' % (json.dumps(key), json.dumps(MODULES[module]),
                                                         json.dumps(name), arity))
    linker = r'''
(define (lazy-relink! key ns name arity)
 (let ((value (bl-get native-global-registry (string-append ns "/" name) #f)))
  (if (not value) (error "lazy relink: no compiled definition" key))
  (native-add-leaf! key (native-arity-entry value arity))))
''' + "\n".join(relink) + "\n"
    # The compiled lazy namespaces and their links come BEFORE the closure, so
    # the closure's initializers (core seeds, top-level defs) already reach
    # compiled LazySeq through the leaf cells, as integrated code would.
    program = (host + "\n" + FOREIGN + (lazy_out / "lazy.scm").read_text() + linker + closure + "\n" + HARNESS
               + (lazy_out / "oracle.scm").read_text()
               + '(display "LAZY_CHECKS ") (display lazy-checks) (display " FAILURES ") (display lazy-failures) (newline)\n'
               + '(exit (if (= lazy-failures 0) 0 1))\n')
    (lazy_out / "check.scm").write_text(program)
    gambit = pathlib.Path(json.loads((BASE / "toolchain-pin.json").read_text())["gambit"])
    return subprocess.run(["timeout", "120", str(gambit / "bin/gsi"), str(lazy_out / "check.scm")],
                          cwd=lazy_out, stdin=subprocess.DEVNULL).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
