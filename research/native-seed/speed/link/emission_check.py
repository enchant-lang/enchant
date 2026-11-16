#!/usr/bin/env python3
"""Assemble a gsi program: host sources + stub slots (published and linked
exactly as native.chunks/link-definition emits) + REAL AOT-emitted
definitions (link-out/inspect.scm) + behavioural checks."""
import pathlib
base = pathlib.Path('/home/othman/.claude/jobs/bbc0cb7e/tmp/wt-link/research/native-seed')
out = pathlib.Path('/home/othman/.claude/jobs/bbc0cb7e/tmp/link-out')


def ident(s):
    return 'v' + ''.join('_%d' % ord(c) for c in s)


def text(s):
    return '"' + s + '"'


def stub(ns, name, fixed, variadic, value):
    b = ident(ns + '/' + name)
    cells = [b + '$%d' % n for n in fixed] + ([b + '$v'] if variadic is not None else []) + [b + '$g']
    setters = ''.join(' (set! %s$%d (native-arity-entry value %d))' % (b, n, n) for n in fixed)
    if variadic is not None:
        setters += ' (set! %s$v (native-variadic-entry value %s))' % (b, text(ns + '/' + name))
    return ('(define %s %s)\n(native-register! %s %s %s)\n' % (b, value, text(ns), text(name), b)
            + '(native-register-arities! %s %s (bl-vec (list %s)) %s)\n' % (
                text(ns), text(name), ' '.join(map(str, fixed)), 'bl-nil' if variadic is None else variadic)
            + ''.join('(define %s #f)\n' % c for c in cells)
            + '(native-link! %s %s (lambda (value) (set! %s value)%s) (lambda (value) (set! %s$g value)))\n' % (
                text(ns), text(name), b, setters, b))


stubs = ''.join([
    stub('native.scheme', 'literal', [1], None, '(lambda (v) (number->string v))'),
    stub('clojure.string', 'join', [1, 2], None,
         '(case-lambda ((xs) (apply string-append xs)) ((sep xs) (if (null? xs) "" '
         '(let loop ((acc (car xs)) (xs (cdr xs))) (if (null? xs) acc (loop (string-append acc sep (car xs)) (cdr xs)))))))'),
    stub('rt', 'map', [2], None, '(lambda (f xs) (map (lambda (x) (bl-invoke f (list x))) xs))'),
    stub('core', 'reduce', [2, 3], None,
         '(case-lambda ((f xs) (error "unused")) ((f acc xs) (let loop ((acc acc) (xs xs)) '
         '(if (null? xs) acc (loop (bl-invoke f (list acc (car xs))) (cdr xs))))))'),
    stub('core', 'to-list', [1], None, '(lambda (x) (error "unused"))'),
])
I = ident


def cell(slot, suffix=''):
    return I(slot) + suffix


checks = r'''
(define link-emission-checks 0)
(define (check label ok)
 (if (not ok) (error (string-append "link emission check failed: " label)))
 (set! link-emission-checks (+ link-emission-checks 1)))
(define (raises? thunk) (let ((r #f)) (with-exception-catcher (lambda (e) (set! r e)) thunk) r))
(check "leaf direct call: pos-line" (= 7 (POSLINE1 (bl-make-tuple 7 8))))
(check "named arithmetic: inc" (= 6 (INC1 5)))
(check "multi fixed arm 1" (= 4 (MIN1 4)))
(check "multi fixed arm 2" (= 3 (MIN2 5 3)))
(check "variadic arm + global reduce" (= 1 (MINV 5 3 '(4 1 2))))
(check "variadic arm of a zero-fixed multi" (bl-equal? (bl-make-tuple 1 2) (TUPLEV '(1 2))))
(check "global + invoke fast path + arity entry" (string=? "1 2 3" (LITITEMS1 '(1 2 3))))
(let ((e (raises? (lambda () (REFUSE1 "why")))))
 (check "variadic remote then leaf raise" (and e (native-raised? e)
   (bl-equal? (native-exception-reason e) (bl-make-tuple (bl-key "invalid_namespace_require") "why")))))
;; Redefinition through native-register! reaches direct remote callers.
(native-register! "rt" "map" (lambda (f xs) (map (lambda (x) (bl-invoke f (list (* 10 x)))) xs)))
(check "register! redefinition of a remote target" (string=? "10 20" (LITITEMS1 '(1 2))))
(native-register! "core" "inc" (lambda (x) (+ x 100)))
(check "register! redefinition of a direct slot" (= 105 (INC1 5)))
;; Redefinition through native-intern reaches global (value) references.
(native-intern "clojure.string" "join" (lambda (sep xs) (apply string-append (cons "<" xs))))
(check "intern redefinition of a global reference" (string=? "<1020" (LITITEMS1 '(1 2))))
(native-intern "clojure.string" "join" (bl-make-tuple (bl-key "$macro") (lambda (sep xs) "macro-fn")))
(check "macro tuple unwrapped for a global reference" (string=? "macro-fn" (LITITEMS1 '(1))))
(native-intern "clojure.string" "join"
 (bl-make-tuple (bl-key "$blfn") (bl-map 2 (lambda (sep xs) "multi-2")) bl-nil))
(check "invoke fast path hands a $blfn to bl-invoke" (string=? "multi-2" (LITITEMS1 '(1))))
(native-intern "clojure.string" "join" (bl-key "nope"))
(check "invoke fast path keeps keyword-as-function semantics"
 (bl-equal? (bl-invoke (bl-key "nope") (list " " (list "10"))) (LITITEMS1 '(1))))
((native-leaf "Elixir.BeamLisp.Env/delete_key/1") (native-row "clojure.string" "join"))
(check "row deletion restores the compiled global" (string=? "10 20" (LITITEMS1 '(1 2))))
;; Leaf replacement reaches its direct callers.
(let ((original (native-leaf "erlang/element/2")))
 (native-replace-leaf! "erlang/element/2" (lambda (i t) 'replaced))
 (check "replaced leaf reaches direct callers" (eq? 'replaced (POSLINE1 (bl-make-tuple 7 8))))
 (native-replace-leaf! "erlang/element/2" original))
(check "restored leaf" (= 7 (POSLINE1 (bl-make-tuple 7 8))))
;; Global view of an emitted definition and the dynamic path agree.
(check "dynamic remote equals linked result" (= 7 ((native-remote "Elixir.BeamLisp.Ns.Reader/pos-line/1") (bl-make-tuple 7 8))))
(display "link emission checks: ") (display link-emission-checks) (newline)
'''
subst = {
    'POSLINE1': cell('reader/pos-line', '$1'), 'INC1': cell('core/inc', '$1'),
    'MIN1': cell('core/min', '$1'), 'MIN2': cell('core/min', '$2'), 'MINV': cell('core/min', '$v'),
    'TUPLEV': cell('core/tuple', '$v'), 'LITITEMS1': cell('native.scheme/literal-items', '$1'),
    'REFUSE1': cell('host.compiler-data/namespace_require_refuse!', '$1'),
}
for k, v in subst.items():
    checks = checks.replace(k, v)
host = ['host.scm', 'host/host-values.scm', 'host/host-leaves.scm', 'host/host-lazy.scm',
        'host/host-extra.scm', 'host/host-compiler.scm']
bundle = ('(native-install-bundle! (bl-map (bl-key "namespace-modules") (bl-vec (list '
          '(bl-vec (list "reader" (bl-key "Elixir.BeamLisp.Ns.Reader") (bl-key "Elixir.BeamLisp.Ns.Reader")))))'
          ' (bl-key "core-links") (bl-vec (list)) (bl-key "resolution") bl-nil))\n')
program = '\n'.join((base / p).read_text() for p in host) + '\n' + bundle + stubs + (out / 'inspect.scm').read_text() + checks
(out / 'link-emission-check.scm').write_text(program)
print(out / 'link-emission-check.scm')
