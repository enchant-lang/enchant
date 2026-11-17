#!/usr/bin/env python3
"""SERVICES differential: run the natively emitted host modules in gsi.

Usage: check.py EMIT-OUT [PRELUDE]
EMIT-OUT holds emit.bl's <ns>.scm files and oracle.scm (BEAM outcomes).
PRELUDE defaults to the integrated round-1 build's prelude.scm; its host part
is replaced by THIS checkout's host sources, so deleted leaves stay deleted.
"""
import json
import pathlib
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parents[2]
MAIN = pathlib.Path('/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/'
                    'native-speed/research/native-seed/out/speed-build/prelude.scm')
HOST = ["host.scm", "host/host-values.scm", "host/host-leaves.scm", "host/host-lazy.scm",
        "host/host-extra.scm", "host/host-compiler.scm", "host/host-match.scm", "host/host-kernel.scm"]
MODULES = [("host.emit", "Elixir.BeamLisp.Emit"), ("host.link", "Elixir.BeamLisp.Link"),
           ("host.server", "Elixir.BeamLisp.Server"), ("host.compiler", "Elixir.BeamLisp.Compiler")]
DELETED = ["Elixir.BeamLisp.Server/callback/1", "Elixir.BeamLisp.Server/callback_order/0",
           "Elixir.BeamLisp.Server/return_constructor_shapes/0", "Elixir.BeamLisp.Server/module_for/2",
           "Elixir.BeamLisp.Emit/module_for/1", "Elixir.BeamLisp.Emit/base_module_for/1",
           "Elixir.BeamLisp.Link/module_for/1", "Elixir.BeamLisp.Compiler/read_data/1",
           "Elixir.BeamLisp.Link/settle/0"] + ["Elixir.BeamLisp.Server/%s" % k for k in (
               "start/1", "start/2", "start/3", "start_link/1", "start_link/2", "start_link/3",
               "call/2", "call/3", "cast/2", "stop/1", "stop/2")]
SDK_SOURCE = pathlib.Path('/nix/store/br0d0abczvbv0rqivpr533a5a0jd1zxq-source')

HARNESS = r'''
(define services-checks 0)
(define services-failures 0)
(define (services-run thunk)
 (with-exception-catcher (lambda (e) (vector 'raised)) (lambda () (vector 'ok (thunk)))))
(define (services-check label thunk expected)
 (let ((actual (services-run thunk)))
  (set! services-checks (+ services-checks 1))
  (if (not (and (eq? (vector-ref actual 0) (vector-ref expected 0))
                (or (eq? (vector-ref actual 0) 'raised)
                    (bl-key-equal? (vector-ref actual 1) (vector-ref expected 1)))))
   (begin (set! services-failures (+ services-failures 1))
    (display "SERVICES_FAIL ") (display label) (display " ")
    (write (list 'native actual 'beam expected)) (newline)))))
'''


def ident(s):
    return 'v' + ''.join('_%d' % ord(c) for c in s)


def main(argv):
    emitted = pathlib.Path(argv[0]).resolve()
    prelude = pathlib.Path(argv[1]) if len(argv) > 1 else MAIN
    text = prelude.read_text()
    tail = text[text.index('\n(native-install-bundle! ') + 1:]
    host = '\n'.join((BASE / p).read_text() for p in HOST) + '\n'
    # native-text.scm is FFI: load the round-1 build's compiled addon, as
    # prepare-host.py does (native-text.scm is unchanged here).
    host += '(load %s)\n' % json.dumps(str(MAIN.parent / 'text.o1'))
    names = ''.join('(native-declare-ns "%s")\n(set! native-module-names (bl-assoc native-module-names "%s" "%s"))\n'
                    % (ns, module, ns) for ns, module in MODULES)
    modules = ''.join((emitted / (ns + '.scm')).read_text() for ns, _ in MODULES)
    absent = ''.join('(services-check "leaf deleted: %s" (lambda () (native-map-has? native-leaf-registry "%s")) (vector \'ok #f))\n'
                     % (k, k) for k in DELETED)
    # The linked cells (what AOT callers use) agree with the dynamic remote.
    cells = ('(services-check "cell host.server/callback$1" (lambda () (%s$1 "init"))'
             ' (vector \'ok (bl-make-tuple (bl-key "init") 1 (bl-key "vector"))))\n'
             '(services-check "cell host.emit/base_module_for$1" (lambda () (%s$1 "a.b"))'
             ' (vector \'ok (bl-key "Elixir.BeamLisp.Ns.A.B")))\n') % (
        ident('host.server/callback'), ident('host.emit/base_module_for'))
    # Compiled settle answers :ok natively (no ETS registry). The service leaf
    # boot_namespaces equals the pinned SDK's sorted priv/boot/*.bl wildcard
    # minus data-readers.
    boot = sorted(p.stem for p in (SDK_SOURCE / 'priv/boot').glob('*.bl') if p.stem != 'data-readers')
    cells += ('(services-check "compiled Link/settle/0 without an ETS registry" (lambda () ((native-remote "Elixir.BeamLisp.Link/settle/0")))'
              ' (vector \'ok (bl-key "ok")))\n'
              '(services-check "service Tiers/boot_namespaces/0 = pinned priv/boot" '
              '(lambda () ((native-remote "Elixir.BeamLisp.Tiers/boot_namespaces/0"))) (vector \'ok (list %s)))\n'
              % ' '.join('"%s"' % n for n in boot))
    report = ('(display "SERVICES_CHECKS ") (display services-checks) (display " FAILURES ") '
              '(display services-failures) (newline) (exit (if (= services-failures 0) 0 1))\n')
    program = emitted / 'services-check.scm'
    program.write_text(host + tail + names + modules + HARNESS + absent + cells
                       + (emitted / 'oracle.scm').read_text() + report)
    gambit = pathlib.Path(json.loads((BASE / 'toolchain-pin.json').read_text())['gambit'])
    return subprocess.run(['timeout', '120', str(gambit / 'bin/gsi'), str(program)],
                          cwd=emitted, stdin=subprocess.DEVNULL).returncode


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
