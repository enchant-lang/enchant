;; Append after pure host + host-values/leaves/lazy/extra + host-compiler.
;; No compiled BL/source-frame helper is required. Restore every registry so
;; the same process can continue with the existing source-frame fixture.
(define native-cache-checks 0)
(define (native-cache-check label ok)
 (if (not ok) (error (string-append "native compiler-cache check failed: " label)))
 (set! native-cache-checks (+ native-cache-checks 1)))
(let ((saved-leaves native-leaf-registry) (saved-modules native-module-names)
      (saved-stubs native-stub-names) (saved-arities native-export-arities)
      (saved-globals native-global-registry))
 (dynamic-wind
  (lambda () #f)
  (lambda ()
   ;; An admitted compiled function returns one stable dispatch wrapper.
   ;; Source redefinition must update the behavior of that SAME wrapper.
   (set! native-module-names
    (bl-assoc native-module-names "Elixir.NativeCacheCompiled" "native.cache-one"))
   (native-register! "native.cache-one" "pick" (lambda (x) (+ x 10)))
   (native-register-arities! "native.cache-one" "pick" (bl-vec '(1)) bl-nil)
   (let* ((key "Elixir.NativeCacheCompiled/pick/1") (first (native-remote key)))
    (native-cache-check "positive compiled wrapper reused" (eq? first (native-remote key)))
    (native-cache-check "initial compiled behavior" (= 15 (bl-invoke first '(5))))
    (native-register! "native.cache-one" "pick" (lambda (x) (+ x 100)))
    (native-cache-check "same escaped wrapper reads redefined live slot" (= 105 (bl-invoke first '(5))))
    (native-cache-check "global value change preserves cached dispatch identity" (eq? first (native-remote key)))
    ;; Removing the selected value must retire an already escaped wrapper's
    ;; previous value. Readding it under a new root must recover the SAME
    ;; wrapper; no missing-slot observation is sticky across registry roots.
    (set! native-global-registry
     (native-map-remove native-global-registry "native.cache-one/pick"))
    (let ((refused #f))
     (with-exception-catcher (lambda (e) (set! refused #t))
      (lambda () (bl-invoke first '(5))))
     (native-cache-check "held compiled wrapper cannot use a removed slot value" refused))
    (let ((refused #f))
     (with-exception-catcher (lambda (e) (set! refused #t))
      (lambda () (bl-invoke first '(5))))
     (native-cache-check "removed slot remains absent within the same root" refused))
    (native-register! "native.cache-one" "pick" (lambda (x) (+ x 100)))
    (native-cache-check "held compiled wrapper sees readded slot value" (= 105 (bl-invoke first '(5))))
    (native-cache-check "slot removal and readdition preserve dispatch membership identity"
     (eq? first (native-remote key)))
    ;; Arity admission changes invalidate resolutions even when this arity
    ;; remains present. An unadmitted MFA never becomes a cached negative.
    (native-cache-check "unadmitted second arity absent"
     (not (native-remote-available? "Elixir.NativeCacheCompiled" "pick" 2)))
    (let ((pending (native-remote "Elixir.NativeCacheCompiled/pick/2")))
     (native-cache-check "unadmitted compiled wrapper remains uncached"
      (not (eq? pending (native-remote "Elixir.NativeCacheCompiled/pick/2")))))
    (native-register! "native.cache-one" "pick"
     (bl-tuple (list (bl-key "$blfn")
      (bl-map 1 (lambda (x) (+ x 100)) 2 (lambda (a b) (+ a b 100))) bl-nil)))
    (native-register-arities! "native.cache-one" "pick" (bl-vec '(1 2)) bl-nil)
    (native-cache-check "arity ledger change invalidates old positive wrapper"
     (not (eq? first (native-remote key))))
    (native-cache-check "new exact arity admitted"
     (native-remote-available? "Elixir.NativeCacheCompiled" "pick" 2))
    (let ((second (native-remote "Elixir.NativeCacheCompiled/pick/2")))
     (native-cache-check "new exact arity invoked" (= 107 (bl-invoke second '(3 4))))
     (native-cache-check "new exact arity now cached"
      (eq? second (native-remote "Elixir.NativeCacheCompiled/pick/2"))))
    ;; The physical module alias is part of dispatch identity. A held old
    ;; wrapper retains its original resolved namespace, as before caching.
    (native-register! "native.cache-two" "pick" (lambda (x) (+ x 200)))
    (native-register-arities! "native.cache-two" "pick" (bl-vec '(1)) bl-nil)
    (let ((before (native-remote key)))
     (set! native-module-names
      (bl-assoc native-module-names "Elixir.NativeCacheCompiled" "native.cache-two"))
     (let ((after (native-remote key)))
      (native-cache-check "module alias change invalidates positive wrapper" (not (eq? before after)))
      (native-cache-check "new lookup follows replacement module alias" (= 205 (bl-invoke after '(5))))
      (native-cache-check "previously escaped wrapper keeps resolved namespace" (= 105 (bl-invoke before '(5)))))))
   ;; Raw registry root replacement must retire a previously cached value.
   ;; Replacement is fixture-owned; the public registration API still refuses
   ;; duplicate keys. No production registry key or value is overwritten.
   (native-add-leaf! "Elixir.NativeCacheRaw/probe/1" (lambda (x) (+ x 1)))
   (let ((before (native-remote "Elixir.NativeCacheRaw/probe/1")))
    (native-cache-check "raw positive behavior" (= 8 (bl-invoke before '(7))))
    (let ((replacement (bl-register-callable! (lambda (x) (+ x 2)) 1)))
     (set! native-leaf-registry
      (bl-assoc native-leaf-registry "Elixir.NativeCacheRaw/probe/1" replacement))
     (let ((after (native-remote "Elixir.NativeCacheRaw/probe/1")))
      (native-cache-check "raw registry replacement invalidates cached callable" (eq? after replacement))
      (native-cache-check "raw replacement behavior observed" (= 9 (bl-invoke after '(7))))
      (native-cache-check "raw replacement does not rewrite escaped function" (= 8 (bl-invoke before '(7)))))))
   ;; A failed lookup is observable now but cannot stick after real admission.
   (let ((refused #f))
    (with-exception-catcher (lambda (e) (set! refused #t))
     (lambda () (native-remote "Elixir.NativeCacheLater/soon/0")))
    (native-cache-check "missing namespace initially refuses" refused))
   (native-add-leaf! "Elixir.NativeCacheLater/soon/0" (lambda () 72))
   (native-cache-check "negative before admission is not sticky"
    (= 72 (bl-invoke (native-remote "Elixir.NativeCacheLater/soon/0") '())))
   ;; The first slash ends the module; the last ends the function. A slash
   ;; inside the function must not be read as an empty name or an arity.
   (set! native-module-names
    (bl-assoc native-module-names "Elixir.NativeCacheSlash" "native.cache-slash"))
   (native-register! "native.cache-slash" "/" (lambda (a b) (quotient a b)))
   (native-register-arities! "native.cache-slash" "/" (bl-vec '(2)) bl-nil)
   (let ((slash (native-remote "Elixir.NativeCacheSlash///2")))
    (native-cache-check "slash function exact MFA invokes" (= 12 (bl-invoke slash '(84 7))))
    (native-cache-check "slash function exact MFA caches"
     (eq? slash (native-remote "Elixir.NativeCacheSlash///2"))))
   (native-cache-check "raw slash-equals function exact MFA invokes"
    (bl-invoke (native-remote "erlang//=/2") '(1 2)))
   ;; make_fun captures before module initialization, computes its MFA once,
   ;; and refreshes a positive target under the same registry root epochs.
   (let ((make-fun (native-leaf "erlang/make_fun/3")))
    (native-add-leaf! "Elixir.NativeMakeRaw/probe/1" (lambda (x) (+ x 1)))
    (let ((saved-atom-name native-atom-name) (conversions 0)
          (module (bl-key "Elixir.NativeMakeRaw")) (function (bl-key "probe")))
     (dynamic-wind
      (lambda ()
       (set! native-atom-name (lambda (value)
        (if (or (eq? value module) (eq? value function)) (set! conversions (+ conversions 1)))
        (saved-atom-name value))))
      (lambda ()
       (let ((captured (bl-invoke make-fun (list module function 1))))
        (native-cache-check "make_fun returns genuine Scheme procedure" (procedure? captured))
        (native-cache-check "make_fun preserves exact accepted arity" (native-callable-accepts? captured 1))
        (native-cache-check "make_fun preserves rejected arity" (not (native-callable-accepts? captured 2)))
        (native-cache-check "make_fun computes atom names at creation" (= conversions 2))
        (native-cache-check "make_fun first positive raw target" (= 8 (bl-invoke captured '(7))))
        (native-cache-check "make_fun warm positive raw target" (= 9 (bl-invoke captured '(8))))
        (native-cache-check "make_fun does not rebuild key on invocation" (= conversions 2))
        (set! native-leaf-registry
         (bl-assoc native-leaf-registry "Elixir.NativeMakeRaw/probe/1"
          (bl-register-callable! (lambda (x) (+ x 20)) 1)))
        (native-cache-check "make_fun raw registry replacement refreshes target" (= 27 (bl-invoke captured '(7))))
        (native-cache-check "make_fun replacement keeps original computed key" (= conversions 2))
        (let ((refused #f))
         (with-exception-catcher (lambda (e) (set! refused #t))
          (lambda () (bl-invoke captured '(1 2))))
         (native-cache-check "make_fun still refuses wrong invocation arity" refused))))
      (lambda () (set! native-atom-name saved-atom-name))))
    (let ((late (bl-invoke make-fun (list (bl-key "Elixir.NativeMakeLater") (bl-key "ready") 0))))
     (native-cache-check "make_fun creation does not resolve an uninitialized module" (procedure? late))
     (let ((refused #f))
      (with-exception-catcher (lambda (e) (set! refused #t)) (lambda () (bl-invoke late '())))
      (native-cache-check "make_fun unadmitted first invocation refuses" refused))
     (native-add-leaf! "Elixir.NativeMakeLater/ready/0" (lambda () 73))
     (native-cache-check "make_fun negative first lookup is not sticky" (= 73 (bl-invoke late '()))))
    (set! native-module-names
     (bl-assoc native-module-names "Elixir.NativeMakeCompiled" "native.make-one"))
    (native-register! "native.make-one" "pick" (lambda (x) (+ x 10)))
    (native-register-arities! "native.make-one" "pick" (bl-vec '(1)) bl-nil)
    (let ((compiled (bl-invoke make-fun (list (bl-key "Elixir.NativeMakeCompiled") (bl-key "pick") 1))))
     (native-cache-check "make_fun initial compiled slot" (= 15 (bl-invoke compiled '(5))))
     (native-register! "native.make-one" "pick" (lambda (x) (+ x 100)))
     (native-cache-check "make_fun cached compiled target reads live redefinition" (= 105 (bl-invoke compiled '(5))))
     (native-register! "native.make-two" "pick" (lambda (x) (+ x 200)))
     (native-register-arities! "native.make-two" "pick" (bl-vec '(1)) bl-nil)
     (set! native-module-names
      (bl-assoc native-module-names "Elixir.NativeMakeCompiled" "native.make-two"))
     (native-cache-check "make_fun module alias replacement refreshes target" (= 205 (bl-invoke compiled '(5)))))
    (let ((slash (bl-invoke make-fun (list (bl-key "Elixir.NativeCacheSlash") (bl-key "/") 2))))
     (native-cache-check "make_fun slash function exact key" (= 7 (bl-invoke slash '(49 7)))))))
  (lambda ()
   (set! native-leaf-registry saved-leaves)
   (set! native-module-names saved-modules)
   (set! native-stub-names saved-stubs)
   (set! native-export-arities saved-arities)
   (set! native-global-registry saved-globals)
   (native-refresh-remote-cache!))))
(display "native compiler-cache checks: ") (display native-cache-checks) (newline)
