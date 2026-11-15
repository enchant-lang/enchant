;; Host transport ABI only: these tiny step functions publish fixed action
;; records; they do not decode BL/ANF or replace any authored Source function.
(define call-slots-checks 0)
(define (call-slots-check label ok)
 (if (not ok) (error "C rooted call-slots transport ABI" label))
 (set! call-slots-checks (+ call-slots-checks 1)))
(define (call-slots-refused? thunk)
 (with-exception-catcher (lambda (exception) #t) (lambda () (thunk) #f)))
(define (call-slots-run action function values tail?)
 (let* ((slots (let loop ((left values) (i 3))
                (if (null? left) '() (cons i (loop (cdr left) (+ i 1))))))
        (frame (make-vector (+ 3 (length values)) bl-nil))
        (unit (vector
         (lambda (machine)
          (if (= (vector-ref machine 1) 0)
           (begin
            (vector-set! machine 4 (vector-ref (vector-ref machine 2) 2))
            (vector-set! machine 5 1) (vector-set! machine 6 77)
            (vector-set! machine 7 (if (= action 6) slots values))
            (vector-set! machine 8 tail?)
            (vector-set! machine 11 (bl-map (bl-key "fn") "transport-call" (bl-key "call") (bl-key "direct")))
            action)
           (begin (vector-set! machine 4 (vector-ref (vector-ref machine 2) 1)) 3)))
         '#() '#()))
        (machine (vector unit 0 frame '() bl-nil 0 0 '() #f bl-nil
                  (list (bl-map (bl-key "fn") "transport-caller")) bl-nil seed-critical #t)))
  (vector-set! frame 2 function)
  (for-each (lambda (slot value) (vector-set! frame slot value)) slots values)
  (native-c-drive machine)))
(call-slots-check 'abi2 (= 2 native-c-action-abi))
(call-slots-check 'abi2-admission (bl-is-nil (native-c-require-action-abi! 2)))
(call-slots-check 'abi1-refusal (call-slots-refused? (lambda () (native-c-require-action-abi! 1))))
(call-slots-check 'inexact-abi-refusal (call-slots-refused? (lambda () (native-c-require-action-abi! 2.0))))
(call-slots-check 'nonnumber-abi-refusal (call-slots-refused? (lambda () (native-c-require-action-abi! #f))))
(let ((old-gc native-c-gc-between-steps?) (old-critical seed-critical))
 (dynamic-wind
  (lambda () (set! native-c-gc-between-steps? #t))
  (lambda ()
   (let* ((f (bl-register-callable! (lambda () 17) 0))
          (collections native-c-forced-gc-count))
    (call-slots-check 'zero-argument-action6 (= 17 (call-slots-run 6 f '() #f)))
    (call-slots-check 'zero-argument-generic-parity
     (= (call-slots-run 6 f '() #f) (call-slots-run 2 f '() #f)))
    (call-slots-check 'actual-gc-before-action (> native-c-forced-gc-count collections)))
   (let* ((first (bl-map (bl-key "payload") (bl-vec '(1 2 3))))
          (second (bl-register-callable! (lambda () first) 0))
          (f (bl-register-callable! (lambda (a b) (list a b)) 2))
          (actual (call-slots-run 6 f (list first second) #f)))
    (call-slots-check 'argument-order-and-identity
     (and (eq? first (car actual)) (eq? second (cadr actual))))
    (call-slots-check 'closure-capture-survives-before-action-gc
     (eq? first (bl-invoke (cadr actual) '())))
    (call-slots-check 'generic-value-parity
     (bl-equal? actual (call-slots-run 2 f (list first second) #f)))
    (call-slots-check 'tail-value-parity
     (bl-equal? (call-slots-run 6 f (list first second) #t)
                (call-slots-run 2 f (list first second) #t))))
   (let ((f (bl-register-callable! (lambda (x) x) 1)) (fused #f) (generic #f))
    (with-exception-catcher (lambda (exception) (set! fused exception))
     (lambda () (call-slots-run 6 f '(1 2) #f)))
    (with-exception-catcher (lambda (exception) (set! generic exception))
     (lambda () (call-slots-run 2 f '(1 2) #f)))
    (call-slots-check 'wrong-arity-same-exception-class
     (and (wrong-number-of-arguments-exception? fused) (wrong-number-of-arguments-exception? generic)))
    (call-slots-check 'wrong-arity-same-target
     (eq? (wrong-number-of-arguments-exception-procedure fused)
          (wrong-number-of-arguments-exception-procedure generic)))
    (call-slots-check 'wrong-arity-same-arguments
     (equal? (wrong-number-of-arguments-exception-arguments fused)
             (wrong-number-of-arguments-exception-arguments generic))))
   (let* ((f (bl-register-callable! (lambda (a b) (list a b)) 2))
          (v (bl-register-callable! (lambda (head rest) (list head rest)) 2))
          (multi (bl-tuple (list (bl-key "$blfn") (bl-map 2 f) (bl-tuple (list 1 v))))))
    (call-slots-check 'multi-fixed-clauses
     (equal? '(1 2) (call-slots-run 6 multi '(1 2) #f)))
    (call-slots-check 'multi-variadic-packing
     (equal? '(1 (2 3)) (call-slots-run 6 multi '(1 2 3) #f)))
    (call-slots-check 'multi-variadic-generic-parity
     (bl-equal? (call-slots-run 6 multi '(1 2 3) #f)
                (call-slots-run 2 multi '(1 2 3) #f))))
   (let* ((callee-unit (vector (lambda (machine)
                         (vector-set! machine 4 (bl-vec (vector-ref (vector-ref machine 2) 0))) 3)
                         '#() '#()))
          (callee (native-c-new-closure callee-unit
                    (list 0 8 '() (bl-map (bl-key "arity") 2 (bl-key "fn") "actual-callee")) '()))
          (a (bl-vec '(7 8))) (b (bl-map (bl-key "held") 9))
          (actual (call-slots-run 6 callee (list a b) #t)))
    (call-slots-check 'c-entry-after-tail-frame-clear
     (and (eq? a (bl-nth actual 0)) (eq? b (bl-nth actual 1))))
    (call-slots-check 'c-entry-nontail-parity
     (bl-equal? actual (call-slots-run 6 callee (list a b) #f)))
    (call-slots-check 'c-entry-generic-parity
     (bl-equal? actual (call-slots-run 2 callee (list a b) #t))))
   (let ((f (bl-register-callable! (lambda () (bl-get (car (native-logical-frames)) (bl-key "fn"))) 0)))
    (call-slots-check 'source-callsite-visible
     (equal? "transport-call" (call-slots-run 6 f '() #f)))
    (call-slots-check 'source-callsite-generic-parity
     (equal? (call-slots-run 6 f '() #f) (call-slots-run 2 f '() #f))))
   (let ((original native-c-resolve-call) (calls 0)
         (f (bl-register-callable! (lambda (x) x) 1))
         (replacement (bl-register-callable! (lambda (x) (+ x 100)) 1)))
    (dynamic-wind
     (lambda () (set! native-c-resolve-call (lambda (callee args)
      (set! calls (+ calls 1))
      (if (eq? callee f) (cons replacement '(7)) (original callee args)))))
     (lambda ()
      (call-slots-check 'planner-target-and-arguments (= 107 (call-slots-run 6 f '(1) #f)))
      (call-slots-check 'planner-once-per-call (= calls 1))
      (call-slots-check 'planner-generic-parity
       (= (call-slots-run 6 f '(1) #f) (call-slots-run 2 f '(1) #f)))
      (call-slots-check 'planner-both-paths-observed (= calls 3)))
     (lambda () (set! native-c-resolve-call original))))
   (let* ((f (bl-register-callable! (lambda (x) (h-critical-enter) x) 1))
          (before seed-critical) (value (call-slots-run 6 f '(7) #t)))
    (call-slots-check 'tail-critical-value (= value 7))
    (call-slots-check 'tail-critical-owner-restored (= seed-critical before))))
  (lambda () (set! native-c-gc-between-steps? old-gc) (set! seed-critical old-critical))))
(display "NATIVE_C_CALL_SLOTS_ABI_PASS ") (display call-slots-checks) (newline)
