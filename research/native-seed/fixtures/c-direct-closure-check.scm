;; Differential host-entry ABI only. No Source/ANF body is decoded or replaced.
(define c-direct-closure-checks 0)
(define (closure-dispatch-check label truth)
 (if (not truth) (error "C direct-closure dispatch ABI" label))
 (set! c-direct-closure-checks (+ c-direct-closure-checks 1)))
(let* ((saved-tick native-c-noactor-tick-enabled?)
       (saved-pure native-c-pure-bif-enabled?)
       (saved-gc native-c-gc-between-steps?) (saved-interval native-c-gc-interval)
       (step (lambda (machine) 3))
       (unit (vector step '#() '#() 0 step))
       (caller-unit (vector step '#() '#() 0 step))
       (function (native-c-new-closure unit
        (list 11 8 '(1) (bl-map (bl-key "fn") "callee" (bl-key "arity") 2
                                (bl-key "native-control") #f))
        (list (bl-key "captured")))))
 (define (machine tail?)
  (vector caller-unit 0 (vector '() 10 20 30 40 50 60 70) '()
   bl-nil 2 77 '() tail? bl-nil
   (list (bl-map (bl-key "fn") "caller" (bl-key "call") (bl-key "direct")))
   (bl-map (bl-key "fn") "site" (bl-key "arity") 2 (bl-key "call") (bl-key "direct"))
   seed-critical #t))
 (define (action target arguments slow? tail?)
  (let ((original native-c-direct-closure?) (depth seed-critical)
        (state (machine tail?)))
   (dynamic-wind
    (lambda () (if slow? (set! native-c-direct-closure? (lambda (value) #f))))
    (lambda () (native-c-apply-action state target arguments) state)
    (lambda () (set! native-c-direct-closure? original) (set! seed-critical depth)))))
 (define (same fast slow) (equal? fast slow))
 (define (restore)
  (set! native-c-noactor-tick-enabled? saved-tick)
  (set! native-c-pure-bif-enabled? saved-pure)
  (set! native-c-gc-between-steps? saved-gc)
  (set! native-c-gc-interval saved-interval))
 (with-exception-catcher (lambda (error) (restore) (raise error))
  (lambda ()
   (set! native-c-noactor-tick-enabled? #f) (set! native-c-pure-bif-enabled? #f)
   (set! native-c-gc-between-steps? #f) (set! native-c-gc-interval 0)
   (closure-dispatch-check 'unverified-host-off (not (native-c-direct-closure? function)))
   (set! native-c-noactor-tick-enabled? #t)
   (closure-dispatch-check 'stock-C-positive (native-c-direct-closure? function))
   (closure-dispatch-check 'Scheme-procedure-excluded
    (not (native-c-direct-closure? (lambda () 1))))
   (closure-dispatch-check 'MFA-excluded
    (not (native-c-direct-closure? (native-c-parse-remote "Elixir.Absent/member/2"))))
   (closure-dispatch-check 'multi-excluded
    (not (native-c-direct-closure? (bl-tuple (list (bl-key "$blfn") (bl-map 2 function) bl-nil)))))
   (closure-dispatch-check 'Scheme-predicate-not-widened
    (not (native-c-direct-procedure? function)))
   (let* ((arguments (list 7 8)) (plan (native-c-resolve-call function arguments))
          (fast (action function arguments #f #f))
          (slow (action function arguments #t #f))
          (before native-c-direct-closure-hits))
    (closure-dispatch-check 'stock-plan-is-identity
     (and (eq? (car plan) function) (eq? (cdr plan) arguments)))
    (closure-dispatch-check 'non-tail-state-identical (same fast slow))
    (closure-dispatch-check 'tail-state-identical
     (same (action function arguments #f #t) (action function arguments #t #t)))
    (closure-dispatch-check 'Source-site-preserved
     (string=? "site" (bl-get (car (vector-ref fast 10)) (bl-key "fn"))))
    (closure-dispatch-check 'entry-and-original-args
     (and (= (vector-ref fast 1) 11) (eq? (vector-ref fast 0) unit)
          (eq? (vector-ref (vector-ref fast 2) 0) arguments)))
    (closure-dispatch-check 'captures-and-Source-arity
     (and (eq? (vector-ref (vector-ref fast 2) 1) (bl-key "captured"))
          (= (bl-get (car (vector-ref fast 10)) (bl-key "arity")) 2)))
    (action function arguments #f #f)
    ;; The preceding tail comparison took one positive path too.
    (closure-dispatch-check 'positive-path-counted (= native-c-direct-closure-hits (+ before 2))))
   ;; No new argument normalization/arity gate is inserted before native entry.
   ;; The actual emitted fixed-arity prologue remains covered by Scalar Source.
   (for-each (lambda (arguments)
    (let ((fast (action function arguments #f #f))
          (slow (action function arguments #t #f)))
     (closure-dispatch-check 'arity-and-improper-spine-transport
      (and (same fast slow) (eq? arguments (vector-ref (vector-ref fast 2) 0))))))
    (list '() '(1 2 3) (cons 1 (bl-key "tail"))))
   (let ((depth seed-critical))
    (dynamic-wind
     (lambda () (set! seed-critical 3))
     (lambda ()
      (let ((fast (action function '(7 8) #f #t))
            (slow (action function '(7 8) #t #t)))
       (closure-dispatch-check 'critical-entry-identical (same fast slow))
       (closure-dispatch-check 'critical-entry-base-kept (= (vector-ref fast 12) 3))))
     (lambda () (set! seed-critical depth))))
   ;; Each actual classifier/planner replacement retains its complete path and
   ;; observable hook calls. Snapshots are lexical, not mutable alias guesses.
   (for-each
    (lambda (spec)
     (let ((original (cadr spec)) (install (caddr spec)) (calls 0))
      (dynamic-wind
       (lambda () (install (lambda args (set! calls (+ calls 1)) (apply original args))))
       (lambda ()
        (closure-dispatch-check (list 'hook-refuses (car spec))
         (not (native-c-direct-closure? function)))
        (let ((state (action function '(7 8) #f #f)))
         (closure-dispatch-check (list 'hook-keeps-target (car spec)) (eq? (vector-ref state 0) unit)))
        (closure-dispatch-check (list 'hook-observed (car spec)) (> calls 0)))
       (lambda () (install original)))))
    (list
     (list 'language native-resolve-call (lambda (value) (set! native-resolve-call value)))
     (list 'multi native-multi-callable? (lambda (value) (set! native-multi-callable? value)))
     (list 'remote native-c-remote? (lambda (value) (set! native-c-remote? value)))
     (list 'closure native-c-closure? (lambda (value) (set! native-c-closure? value)))
     (list 'tag bl-tag? (lambda (value) (set! bl-tag? value)))
     (list 'planner native-c-resolve-call (lambda (value) (set! native-c-resolve-call value)))
     (list 'external-base native-c-resolve-without-external-funs
      (lambda (value) (set! native-c-resolve-without-external-funs value)))
     (list 'remote-base native-c-resolve-without-remote
      (lambda (value) (set! native-c-resolve-without-remote value)))
     (list 'direct-procedure native-c-direct-procedure?
      (lambda (value) (set! native-c-direct-procedure? value)))))
   (for-each
    (lambda (spec)
     (let ((original (car spec)) (install (cadr spec)))
      (dynamic-wind
       (lambda () (install (lambda args (apply original args))))
       (lambda ()
        (closure-dispatch-check 'invoker-refuses (not (native-c-direct-closure? function)))
        (closure-dispatch-check 'invoker-keeps-target
         (eq? (vector-ref (action function '(7 8) #f #f) 0) unit)))
       (lambda () (install original)))))
    (list (list bl-invoke (lambda (value) (set! bl-invoke value)))
          (list native-c-fallback-invoke (lambda (value) (set! native-c-fallback-invoke value)))))
   (let* ((original native-logical-frames) (calls 0)
          (parameter (make-parameter '() (lambda (value) (set! calls (+ calls 1)) value)))
          (before calls))
    (dynamic-wind
     (lambda () (set! native-logical-frames parameter))
     (lambda ()
      (closure-dispatch-check 'converter-parameter-refuses (not (native-c-direct-closure? function)))
      (action function '(7 8) #f #f)
      (closure-dispatch-check 'converter-effects-preserved (> calls before)))
     (lambda () (set! native-logical-frames original))))
   (dynamic-wind
    (lambda () (table-set! native-c-external-funs function '#(external)))
    (lambda ()
     (closure-dispatch-check 'external-ledger-entry-refuses (not (native-c-direct-closure? function)))
     (closure-dispatch-check 'external-ledger-keeps-stock-target
      (eq? (vector-ref (action function '(7 8) #f #f) 0) unit)))
    (lambda () (table-set! native-c-external-funs function)))
   (let ((original native-c-external-funs))
    (dynamic-wind
     (lambda () (set! native-c-external-funs (make-table test: eq? weak-keys: #t)))
     (lambda () (closure-dispatch-check 'replacement-ledger-refuses (not (native-c-direct-closure? function))))
     (lambda () (set! native-c-external-funs original))))
   (let ((original native-c-raw-apply2))
    (dynamic-wind
     (lambda () (set! native-c-raw-apply2 function))
     (lambda () (closure-dispatch-check 'backend-raw-apply-alias-refuses (not (native-c-direct-closure? function))))
     (lambda () (set! native-c-raw-apply2 original))))
   (let ((original native-raw-apply))
    (dynamic-wind
     (lambda () (set! native-raw-apply function))
     (lambda () (closure-dispatch-check 'raw-apply-alias-refuses (not (native-c-direct-closure? function))))
     (lambda () (set! native-raw-apply original))))
   (set! native-c-gc-between-steps? #t)
   (closure-dispatch-check 'forced-GC-refuses (not (native-c-direct-closure? function)))
   (set! native-c-gc-between-steps? #f) (set! native-c-gc-interval 997)
   (closure-dispatch-check 'interval-GC-refuses (not (native-c-direct-closure? function)))
   (set! native-c-gc-interval 0)
   (closure-dispatch-check 'stock-restored (native-c-direct-closure? function))))
 (restore))
(if (not (= c-direct-closure-checks 59)) (error "C closure fixture count" c-direct-closure-checks))
(display "NATIVE_C_DIRECT_CLOSURE_ABI_PASS 59") (newline)
