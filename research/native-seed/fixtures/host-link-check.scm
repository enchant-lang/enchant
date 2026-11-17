;; Append after pure host + host-values/leaves/lazy/extra + host-compiler.
;; AOT link cells and the remaining dynamic MFA lookup. No compiled BL is
;; required. Every registry is restored so the same process can continue
;; with the source-frame fixture.
(define native-link-checks 0)
(define (native-link-check label ok)
 (if (not ok) (error (string-append "native link check failed: " label)))
 (set! native-link-checks (+ native-link-checks 1)))
(define (native-link-raises? thunk)
 (let ((raised #f))
  (with-exception-catcher (lambda (e) (set! raised #t)) thunk)
  raised))
(define (native-link-cell name)
 (##global-var-ref (##make-global-var (string->symbol name))))
;; Cells exactly as native.chunks/link-definition emits them for a slot
;; "native.link-one/pick" declaring fixed arities 1 and 2 and a variadic arm.
(define v_link_pick #f)
(define v_link_pick$1 #f)
(define v_link_pick$2 #f)
(define v_link_pick$v #f)
(define v_link_pick$g #f)
(define v_link_seed$g (native-unlinked "native.link-seed" "s"))
(let ((saved-leaves native-leaf-registry) (saved-modules native-module-names)
      (saved-stubs native-stub-names) (saved-arities native-export-arities)
      (saved-globals native-global-registry) (saved-rows native-env-rows)
      (saved-excluded native-excluded-host-leaves))
 (dynamic-wind
  (lambda () #f)
  (lambda ()
   ;; ---- named leaf bindings ----
   (native-link-check "leaf binding name is l + scheme ident"
    (string=? "lv_97_47_98_47_49" (native-leaf-binding-name "a/b/1")))
   (native-link-check "every registered leaf has its named binding"
    (let loop ((pairs (native-map-pairs native-leaf-registry)))
     (or (null? pairs)
      (and (eq? (bl-nth (car pairs) 1) (native-link-cell (native-leaf-binding-name (bl-nth (car pairs) 0))))
           (loop (cdr pairs))))))
   (native-add-leaf! "Elixir.NativeLink/probe/1" (lambda (x) (+ x 1)))
   (native-link-check "new leaf binding is callable directly"
    (= 8 ((native-link-cell (native-leaf-binding-name "Elixir.NativeLink/probe/1")) 7)))
   (native-link-check "dynamic lookup of a leaf is the leaf itself"
    (eq? (native-remote "Elixir.NativeLink/probe/1") (native-leaf "Elixir.NativeLink/probe/1")))
   (native-replace-leaf! "Elixir.NativeLink/probe/1" (lambda (x) (+ x 100)))
   (native-link-check "replaced leaf updates its named binding"
    (= 107 ((native-link-cell (native-leaf-binding-name "Elixir.NativeLink/probe/1")) 7)))
   (native-link-check "replaced leaf retires the dynamic lookup"
    (= 107 ((native-remote "Elixir.NativeLink/probe/1") 7)))
   (native-link-check "replacing an absent leaf is refused"
    (native-link-raises? (lambda () (native-replace-leaf! "Elixir.NativeLink/absent/1" (lambda (x) x)))))
   (native-link-check "duplicate leaf registration is still refused"
    (native-link-raises? (lambda () (native-add-leaf! "Elixir.NativeLink/probe/1" (lambda (x) x)))))

   ;; ---- compiled slot cells ----
   (native-register! "native.link-one" "pick" (lambda (x) (+ x 10)))
   (native-register-arities! "native.link-one" "pick" (bl-vec '(1 2)) 2)
   (native-link! "native.link-one" "pick"
    (lambda (value) (set! v_link_pick value)
     (set! v_link_pick$1 (native-arity-entry value 1)) (set! v_link_pick$2 (native-arity-entry value 2))
     (set! v_link_pick$v (native-variadic-entry value "native.link-one/pick")))
    (lambda (value) (set! v_link_pick$g value)))
   (native-link-check "link initializes the compiled cell" (= 15 (v_link_pick 5)))
   (native-link-check "plain procedure arity entry is the procedure itself" (eq? v_link_pick$1 v_link_pick))
   (native-link-check "link initializes the global view" (eq? v_link_pick$g v_link_pick))
   (native-link-check "plain procedure has no variadic arm"
    (native-link-raises? (lambda () (v_link_pick$v 1 '(2)))))
   (native-register! "native.link-one" "pick" (lambda (x) (+ x 20)))
   (native-link-check "native-register! redefinition reaches the arity cell" (= 25 (v_link_pick$1 5)))
   (native-link-check "native-register! redefinition reaches the global view" (= 25 (v_link_pick$g 5)))
   (let* ((one (lambda (x) (list 'one x))) (two (lambda (x y) (list 'two x y)))
          (rest (lambda (x y more) (list 'rest x y more)))
          (multi (bl-make-tuple (bl-key "$blfn") (bl-map 1 one 2 two) (bl-make-tuple 2 rest))))
    (native-register! "native.link-one" "pick" multi)
    (native-link-check "multi redefinition publishes its fixed arm" (eq? v_link_pick$1 one))
    (native-link-check "multi redefinition publishes its second arm" (eq? v_link_pick$2 two))
    (native-link-check "multi redefinition publishes its variadic arm" (eq? v_link_pick$v rest))
    (native-link-check "variadic arm receives the rest list as the wrapper did"
     (equal? (list 'rest 1 2 '(3 4)) (v_link_pick$v 1 2 '(3 4))))
    (native-link-check "compiled cell holds the multi value itself" (eq? v_link_pick multi))
    (native-register! "native.link-one" "pick" (bl-make-tuple (bl-key "$blfn") (bl-map 1 one) (bl-make-tuple 2 rest)))
    (native-link-check "arity absent from the multi dispatches through bl-invoke"
     (equal? (list 'rest 1 2 '()) (v_link_pick$2 1 2))))
   (native-register! "native.link-one" "pick" bl-nil)
   (native-link-check "nonfunction redefinition keeps the invocation refusal"
    (native-link-raises? (lambda () (v_link_pick$1 5))))
   (native-register! "native.link-one" "pick" (lambda (x) (+ x 10)))
   (native-link-check "function redefinition recovers" (= 15 (v_link_pick$1 5)))

   ;; ---- global view: env rows shadow, macros unwrap ----
   (native-intern "native.link-one" "pick" (lambda (x) (* x 2)))
   (native-link-check "native-intern reaches the global view" (= 10 (v_link_pick$g 5)))
   (native-link-check "native-intern leaves the compiled cells as remote dispatch saw them"
    (= 15 (v_link_pick$1 5)))
   (native-link-check "global view equals live native-global" (eq? v_link_pick$g (native-global "native.link-one" "pick")))
   (native-register! "native.link-one" "pick" (lambda (x) (+ x 30)))
   (native-link-check "register under an env row keeps the row's global view" (= 10 (v_link_pick$g 5)))
   (native-link-check "register under an env row updates the compiled cell" (= 35 (v_link_pick$1 5)))
   (let ((expander (lambda (form env) 'expanded)))
    (native-intern "native.link-one" "pick" (bl-make-tuple (bl-key "$macro") expander))
    (native-link-check "macro tuple is unwrapped in the global view" (eq? v_link_pick$g expander))
    (native-link-check "unwrapped global view equals native-global-exact"
     (eq? v_link_pick$g (native-global-exact "native.link-one" "pick"))))
   ((native-leaf "Elixir.BeamLisp.Env/delete_key/1") (native-row "native.link-one" "pick"))
   (native-link-check "deleting the env row restores the compiled global view" (= 35 (v_link_pick$g 5)))
   ((native-leaf "Elixir.BeamLisp.Env/put_key/2") (native-row "native.link-one" "pick") (lambda (x) x))
   (native-link-check "Env/put_key of a row reaches the global view" (= 5 (v_link_pick$g 5)))

   ;; ---- seeds: global view only ----
   (native-link-global! "native.link-seed" "s" (lambda (value) (set! v_link_seed$g value)))
   (native-link-check "unpublished seed refuses like an undefined var"
    (native-link-raises? (lambda () (v_link_seed$g 1))))
   (native-intern "native.link-seed" "s" (lambda (x) (list 'seed x)))
   (native-link-check "seed intern publishes its global view" (equal? '(seed 1) (v_link_seed$g 1)))

   ;; ---- dynamic MFA lookup (eval context, erlang/apply/3, make_fun/3) ----
   (set! native-module-names (bl-assoc native-module-names "Elixir.NativeLinkCompiled" "native.link-one"))
   (set! native-stub-names (bl-assoc native-stub-names "Elixir.NativeLinkStub" "native.link-stub"))
   (native-link-changed!)
   (let* ((key "Elixir.NativeLinkCompiled/pick/1") (wrapper (native-remote key)))
    (native-link-check "dynamic compiled wrapper calls the slot" (= 35 (wrapper 5)))
    (native-link-check "dynamic compiled wrapper is memoized" (eq? wrapper (native-remote key)))
    (native-link-check "mutable key copy cannot alias the memo"
     (let ((copy (string-copy key))) (eq? wrapper (native-remote copy))))
    (native-register! "native.link-one" "pick" (lambda (x) (+ x 40)))
    (native-link-check "held dynamic wrapper reads the redefined slot" (= 45 (wrapper 5))))
   (let ((rest (lambda (x more) (list x more))))
    (native-register! "native.link-one" "pick"
     (bl-make-tuple (bl-key "$blfn") (bl-map 1 (lambda (x) x)) (bl-make-tuple 1 rest)))
    (native-link-check "dynamic rest-list remote calls the variadic arm"
     (equal? (list 1 '(2 3)) ((native-remote "Elixir.NativeLinkCompiled/pick__bl_v/2") 1 '(2 3)))))
   (native-register! "native.link-one" "pick" (lambda (x) x))
   (native-link-check "dynamic rest-list remote without variadic arm raises"
    (native-link-raises? (lambda () ((native-remote "Elixir.NativeLinkCompiled/pick__bl_v/2") 1 '()))))
   (native-link-check "missing compiled slot raises at call"
    (native-link-raises? (lambda () ((native-remote "Elixir.NativeLinkCompiled/absent/1") 1))))
   (native-link-check "excluded namespace raises at call"
    (native-link-raises? (lambda () ((native-remote "Elixir.NativeLinkStub/f/1") 1))))
   (native-link-check "unknown module raises at lookup"
    (native-link-raises? (lambda () (native-remote "Elixir.NativeLinkNone/f/1"))))
   (native-link-check "invalid key raises at lookup"
    (native-link-raises? (lambda () (native-remote "nokey"))))
   (native-link-check "erlang/apply/3 reaches the compiled slot"
    (= 5 ((native-leaf "erlang/apply/3") (bl-key "Elixir.NativeLinkCompiled") (bl-key "pick") '(5))))

   ;; ---- function_exported/3 memo, retired by explicit publication ----
   (let ((m (bl-key "Elixir.NativeLinkCompiled")) (f (bl-key "pick")))
    (native-link-check "exported fixed arity" (eq? #t (native-remote-available? m f 1)))
    (native-link-check "unexported arity" (eq? #f (native-remote-available? m f 3)))
    (native-link-check "variadic export uses minimum + 1" (eq? #t (native-remote-available? m (bl-key "pick__bl_v") 3)))
    (native-register-arities! "native.link-one" "pick" (bl-vec '(1 3)) bl-nil)
    (native-link-check "arity publication retires the memo" (eq? #t (native-remote-available? m f 3)))
    (native-link-check "retired variadic export" (eq? #f (native-remote-available? m (bl-key "pick__bl_v") 3))))
   (let ((m (bl-key "Elixir.NativeLink")) (f (bl-key "later")))
    (native-link-check "absent leaf is unexported" (eq? #f (native-remote-available? m f 0)))
    (native-add-leaf! "Elixir.NativeLink/later/0" (lambda () 'later))
    (native-link-check "leaf publication retires the memo" (eq? #t (native-remote-available? m f 0))))
   (native-link-check "excluded host leaf is unexported"
    (eq? #f (native-remote-available? (bl-key "Elixir.BeamLisp.Env") (bl-key "check_source_callable!") 1)))
   (native-link-check "string arguments are answered without the memo"
    (eq? #t (native-remote-available? "Elixir.NativeLink" "later" 0)))

   ;; ---- invoke fast path and named arithmetic as emitted ----
   (let ((call (lambda (f) (let ((callee f)) (let* ((a0 (bl-map (bl-key "a") 1)))
                 (if (procedure? callee) (callee a0) (bl-invoke callee (list a0))))))))
    (native-link-check "fast path applies a procedure" (eq? #t (bl-tag? (call (lambda (m) m)) 'map)))
    (native-link-check "fast path sends a keyword to bl-invoke" (= 1 (call (bl-key "a")))))
   (native-link-check "named arithmetic equals bl-arithmetic"
    (let loop ((rows (list (list "add" native-arith-add) (list "sub" native-arith-sub) (list "mul" native-arith-mul)
                           (list "div" native-arith-div) (list "lt" native-arith-lt) (list "gt" native-arith-gt)
                           (list "le" native-arith-le) (list "ge" native-arith-ge) (list "num_eq" native-arith-num-eq))))
     (or (null? rows)
      (let ((op (bl-key (car (car rows)))) (f (cadr (car rows))))
       (and (bl-equal? (bl-arithmetic op 6 3) (f 6 3))
            (bl-equal? (bl-arithmetic op (bl-float 1.5) 2) (f (bl-float 1.5) 2))
            (loop (cdr rows))))))))
  (lambda ()
   (set! native-leaf-registry saved-leaves) (set! native-module-names saved-modules)
   (set! native-stub-names saved-stubs) (set! native-export-arities saved-arities)
   (set! native-global-registry saved-globals) (set! native-env-rows saved-rows)
   (set! native-excluded-host-leaves saved-excluded) (native-link-changed!))))
(display "native link checks: ") (display native-link-checks) (newline)
