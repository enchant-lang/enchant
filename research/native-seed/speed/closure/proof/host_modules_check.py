#!/usr/bin/env python3
"""gsi program: host sources + bundle metadata with :host-modules + the REAL
AOT-emitted host.deferred definitions (chunks.bl inspect) + checks.
Usage: host_modules_check.py NS_DIR INSPECT_SCM OUT_SCM"""
import pathlib, re, sys
base, inspect, out = map(pathlib.Path, sys.argv[1:4])
host = ["host.scm", "host/host-values.scm", "host/host-leaves.scm", "host/host-lazy.scm",
        "host/host-extra.scm", "host/host-compiler.scm", "host/host-match.scm", "host/host-kernel.scm"]
text = inspect.read_text()
# The three host.deferred definitions precede core/memoize in the inspect order.
cut = text.index("(define v_99_111_114_101_47_109_101_109_111_105_122_101 ")
deferred = text[:cut]
ident = lambda s: "v" + "".join("_%d" % ord(c) for c in s)
bundle = ('(native-install-bundle! (bl-map (bl-key "namespace-modules") (bl-vec (list '
          '(bl-vec (list "host.deferred" (bl-key "Elixir.BeamLisp.Ns.Host.Deferred") (bl-key "Elixir.BeamLisp.Ns.Host.Deferred")))))'
          ' (bl-key "host-modules") (bl-vec (list (bl-vec (list "host.compiler-data" (bl-key "Elixir.BeamLisp.CompilerData")))'
          ' (bl-vec (list "host.deferred" (bl-key "Elixir.BeamLisp.Deferred")))))'
          ' (bl-key "core-links") (bl-vec (list)) (bl-key "resolution") bl-nil))\n')
force, realized, isdelay = (ident("host.deferred/" + n) + "$1" for n in ("force", "realized?", "delay?"))
checks = f"""
(define checks 0)
(define (check label ok) (if (not ok) (error "host-modules check failed" label)) (set! checks (+ checks 1)))
(check "module table: pinned Deferred" (equal? (bl-get native-module-names "Elixir.BeamLisp.Deferred" #f) "host.deferred"))
(check "module table: CompilerData from metadata" (equal? (bl-get native-module-names "Elixir.BeamLisp.CompilerData" #f) "host.compiler-data"))
(check "module table: no hard-coded Meta row" (not (bl-get native-module-names "Elixir.BeamLisp.Meta" #f)))
(define made (bl-invoke (native-remote "Elixir.BeamLisp.Deferred/delay/1") (list (lambda () 42))))
(check "compiled delay? on a leaf-made delay" (eq? #t ({isdelay} made)))
(check "compiled delay? on 1" (eq? #f ({isdelay} 1)))
(check "compiled realized? before force" (eq? #f ({realized} made)))
(check "compiled force" (equal? 42 ({force} made)))
(check "compiled realized? after force" (eq? #t ({realized} made)))
(check "compiled force of a non-delay" (equal? 7 ({force} 7)))
(check "compiled realized? of a non-delay" (eq? #t ({realized} 7)))
(display "host-modules checks: ") (display checks) (newline)
"""
program = "\n".join((base / p).read_text() for p in host) + "\n" + bundle + deferred + checks
out.write_text(program)
print(out)
