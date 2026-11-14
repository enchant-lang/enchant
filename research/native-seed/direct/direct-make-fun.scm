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
 (let peel ((plan (native-c-resolve-without-external-funs callee arguments)) (seen '()))
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
        (peel (native-c-resolve-without-external-funs (native-c-remote key) args)
              (cons target seen)))))))))))
