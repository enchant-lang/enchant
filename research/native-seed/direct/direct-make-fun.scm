;; Append after direct-remote.scm, BEFORE any rt/seed-core initialization.
;; The Source value remains the original genuine Scheme function and retains
;; its registered arity. Only the C call planner consults this private ledger.
(define native-c-external-funs (make-table test: eq? weak-keys: #t))
(define native-c-original-make-fun (native-remote "erlang/make_fun/3"))
(define native-c-make-fun3
 (native-c-replace-leaf! "erlang/make_fun/3" native-c-original-make-fun
  (lambda (module function arity)
   (let ((forwarder (native-c-original-make-fun module function arity)))
    (if (not (procedure? forwarder)) (error "make_fun host did not return a genuine Scheme function"))
    (table-set! native-c-external-funs forwarder (vector module function arity)) forwarder)) 3))
(define native-c-resolve-without-external-funs native-c-resolve-call)
(set! native-c-resolve-call (lambda (callee arguments)
 (let peel ((plan (native-c-resolve-without-external-funs (native-c-dispatch-view callee) arguments)) (seen '()))
  (let* ((target (car plan)) (args (cdr plan))
         (raw-apply? (or (eq? target native-c-raw-apply2) (eq? target native-raw-apply)))
         (raw-forwarder
          (and raw-apply? (pair? args) (pair? (cdr args)) (null? (cddr args))
               (table-ref native-c-external-funs (car args) #f))))
   (if raw-forwarder
    (begin
     ;; Preserve strict raw apply's list/badfun/badarity validation BEFORE
     ;; selecting the annotated external function's actual physical target.
     (native-check-raw-apply! (car args) (cadr args))
     (peel (native-c-resolve-without-external-funs (car args) (cadr args)) seen))
    (let ((external (and (procedure? target) (table-ref native-c-external-funs target #f))))
     (if (not external) plan
      (begin
       (if (memq target seen) (error "cyclic external-function forwarding metadata"))
       (if (not (= (length args) (vector-ref external 2))) (native-badarg "remote function arity"))
       (let ((key (string-append (native-atom-name (vector-ref external 0)) "/"
                   (native-atom-name (vector-ref external 1)) "/" (number->string (vector-ref external 2)))))
        ;; private static-MFA descriptors never become the Source fun value.
        ;; Resolve language dispatch and raw-apply selection to a final callee;
        ;; this loop invokes no forwarding body and never starts a C machine.
        (peel (native-c-resolve-without-external-funs (native-c-dispatch-view (native-c-remote key)) args)
              (cons target seen)))))))))))

;; Ordinary procedures need no dispatcher/MFA/external-fun transport. Install
;; ONLY after the declared complete planner stack; retain every dynamic hook.
;; These lexical proof identities cannot be retargeted by changing an alias.
(let ((base-invoker native-remote-original-invoke)
      (base-resolver native-invoke-original-resolve)
      (multi-predicate native-multi-callable?)
      (remote-predicate native-c-remote?)
      (planner native-c-resolve-call)
      (external-base native-c-resolve-without-external-funs)
      (remote-base native-c-resolve-without-remote)
      (old-invoker bl-invoke))
 (letrec
  ((direct? (lambda (callee)
    (and (procedure? callee)
         (eq? native-c-fallback-invoke base-invoker)
         (eq? native-resolve-call base-resolver)
         (eq? native-multi-callable? multi-predicate)
         (eq? native-c-remote? remote-predicate)
         (eq? native-c-resolve-call planner)
         (eq? native-c-resolve-without-external-funs external-base)
         (eq? native-c-resolve-without-remote remote-base)
         (eq? bl-invoke invoke)
         (not (eq? callee native-c-raw-apply2))
         (not (eq? callee native-raw-apply))
         (not (table-ref native-c-external-funs callee #f)))))
   (invoke (lambda (callee arguments)
    (if (direct? callee) (apply callee arguments)
     (old-invoker callee arguments)))))
  (set! native-c-direct-procedure? direct?)
  (set! bl-invoke invoke)))

;; Separate from the Scheme-procedure predicate: a C descriptor must still
;; enter the existing C frame/source/critical path, never Scheme apply.
;; Existing opt-ins prove the frozen host's initial parameter has no converter.
(let ((closure? native-c-closure?)
      (base-invoker native-remote-original-invoke)
      (base-resolver native-invoke-original-resolve)
      (multi? native-multi-callable?) (remote? native-c-remote?)
      (tag? bl-tag?) (invoker bl-invoke)
      (direct-procedure? native-c-direct-procedure?)
      (planner native-c-resolve-call)
      (external-base native-c-resolve-without-external-funs)
      (remote-base native-c-resolve-without-remote)
      (logical-frames native-c-initial-logical-frames)
      (external-ledger native-c-external-funs))
 (set! native-c-direct-closure?
  (lambda (callee)
   (and (or native-c-noactor-tick-enabled? native-c-pure-bif-enabled?)
        (closure? callee)
        (not native-c-gc-between-steps?) (eqv? native-c-gc-interval 0)
        (eq? native-c-closure? closure?)
        (eq? native-c-fallback-invoke base-invoker)
        (eq? native-resolve-call base-resolver)
        (eq? native-multi-callable? multi?) (eq? native-c-remote? remote?)
        (eq? bl-tag? tag?) (eq? bl-invoke invoker)
        (eq? native-c-direct-procedure? direct-procedure?)
        (eq? native-c-resolve-call planner)
        (eq? native-c-resolve-without-external-funs external-base)
        (eq? native-c-resolve-without-remote remote-base)
        (eq? native-logical-frames logical-frames)
        (eq? native-c-external-funs external-ledger)
        (not (eq? callee native-c-raw-apply2))
        (not (eq? callee native-raw-apply))
        (not (table-ref external-ledger callee #f))))))

;; Optional four-BIF installer. The complete planner and Source-slot stack
;; must be installed above. Captured identities are private lexical proof data.
(define native-c-pure-bif-seen 0)
(define native-c-pure-bif-steps 0)
(let ((originals (vector (native-leaf "erlang/is_list/1")
                        (native-leaf "erlang/is_integer/1")
                        (native-leaf "erlang/==/2")
                        (native-leaf "erlang/=:=/2")))
      (invoker bl-invoke) (resolver native-resolve-call)
      (fallback native-c-fallback-invoke) (direct? native-c-direct-procedure?)
      (planner native-c-resolve-call) (external-base native-c-resolve-without-external-funs)
      (remote-base native-c-resolve-without-remote)
      (multi? native-multi-callable?) (remote? native-c-remote?) (closure? native-c-closure?)
      (apply-action native-c-apply-action)
      (frame-action native-c-apply-action-without-frame-slots)
      (site-stack native-c-site-stack) (frame-context native-c-frame-call-context)
      (after-step native-c-after-step!) (logical-frames native-logical-frames)
      (owned-step? native-c-owned-step?)
      (nil? bl-is-nil) (get bl-get) (key bl-key) (truthy bl-truthy)
      (key-intern native-key-intern) (scalar-key native-scalar-keyword-intern)
      (utf16-fragment? native-utf16-fragment?) (tag? bl-tag?)
      (raw-apply native-raw-apply) (c-raw-apply native-c-raw-apply2)
      (key-compare bl-key-compare) (key-rank native-key-rank)
      (compare-number native-compare-number) (ratio native-ratio)
      (number-compare native-number-compare) (erlang-number? native-erlang-number?)
      (integer? h-is-int) (float? h-is-float))
 (define (requested? requested bit) (not (= 0 (bitwise-and requested bit))))
 (define (uncaptured? id) (not (table-ref native-c-external-funs (vector-ref originals id) #f)))
 (define (numeric-hooks?)
  (and (eq? native-erlang-number? erlang-number?) (eq? h-is-int integer?) (eq? h-is-float float?)
       (eq? native-number-compare number-compare) (eq? native-ratio ratio)
       (eq? native-compare-number compare-number)))
 (set! native-c-refresh-pure-bifs!
  (lambda (machine)
   (let ((extension (native-c-tick-extension machine)))
    (if extension
     (begin
      ;; No stale authority survives an arbitrary Scheme action/hook.
      (vector-set! extension 2 0) (vector-set! extension 3 originals) (vector-set! extension 4 0)
      (let* ((unit (vector-ref machine 0))
             (requested (if (and (vector? unit) (= (vector-length unit) 5)
                                (exact-integer? (vector-ref unit 3))) (vector-ref unit 3) 0)))
       (if (and native-c-pure-bif-enabled? (> requested 0)
                (eq? native-c-owned-step? owned-step?) (owned-step? machine)
                (not native-c-gc-between-steps?) (eqv? native-c-gc-interval 0)
                (eq? bl-invoke invoker) (eq? native-resolve-call resolver)
                (eq? native-c-fallback-invoke fallback) (eq? native-c-direct-procedure? direct?)
                (eq? native-c-resolve-call planner)
                (eq? native-c-resolve-without-external-funs external-base)
                (eq? native-c-resolve-without-remote remote-base)
                (eq? native-multi-callable? multi?) (eq? native-c-remote? remote?)
                (eq? native-c-closure? closure?) (eq? native-c-apply-action apply-action)
                (eq? native-c-apply-action-without-frame-slots frame-action)
                (eq? native-c-site-stack site-stack) (eq? native-c-frame-call-context frame-context)
                (eq? native-c-after-step! after-step) (eq? native-logical-frames logical-frames)
                (eq? bl-is-nil nil?) (eq? bl-get get) (eq? bl-key key) (eq? bl-truthy truthy)
                (eq? native-key-intern key-intern) (eq? native-scalar-keyword-intern scalar-key)
                (eq? native-utf16-fragment? utf16-fragment?) (eq? bl-tag? tag?)
                (eq? native-raw-apply raw-apply) (eq? native-c-raw-apply2 c-raw-apply))
        (let ((mask 0))
         (if (and (requested? requested 1) (uncaptured? 0)) (set! mask (+ mask 1)))
         (if (and (requested? requested 2) (uncaptured? 1)) (set! mask (+ mask 2)))
         (if (and (requested? requested 4) (uncaptured? 2))
          (begin (set! mask (+ mask 4)) (if (numeric-hooks?) (set! mask (+ mask 8)))))
         (if (and (requested? requested 16) (uncaptured? 3) (eq? bl-key-compare key-compare))
          (begin (set! mask (+ mask 16))
           (if (and (eq? native-key-rank key-rank) (eq? native-compare-number compare-number))
            (set! mask (+ mask 32)))))
         (vector-set! extension 2 mask)))))))))
 (set! native-c-record-pure-bifs!
  (lambda (machine)
   (let ((extension (native-c-tick-extension machine)))
    (if extension
     (let ((seen (vector-ref extension 4)))
      (vector-set! extension 2 0) (vector-set! extension 4 0)
      (if (and (exact-integer? seen) (> seen 0))
       (begin (set! native-c-pure-bif-seen (bitwise-ior native-c-pure-bif-seen seen))
              (set! native-c-pure-bif-steps (+ native-c-pure-bif-steps 1))))))))))

;; Seal only after the complete planner, procedure/C guards and BIF installer.
;; An affected custom hook receives the retained legacy descriptor BEFORE it
;; runs; this capture never blesses an arbitrary replacement as stock.
(set! native-c-symbol-complete-hooks-current?
 (let ((planner native-c-resolve-call)
       (external native-c-resolve-without-external-funs)
       (base native-resolve-call) (multi native-multi-callable?)
       (direct native-c-direct-procedure?) (closure native-c-direct-closure?)
       (invoker bl-invoke) (frames native-logical-frames))
  (lambda ()
   (and (eq? native-c-resolve-call planner)
        (eq? native-c-resolve-without-external-funs external)
        (eq? native-resolve-call base) (eq? native-multi-callable? multi)
        (eq? native-c-direct-procedure? direct) (eq? native-c-direct-closure? closure)
        (eq? bl-invoke invoker) (eq? native-logical-frames frames)))))
