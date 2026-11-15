;; Host ABI fixture, loaded after frozen host + direct-machine. It exercises
;; boundary transport independently of emitted Source policy. No scheduler.
(define native-critical-check-count 0)
(define (native-critical-check label actual expected)
 (if (not (equal? actual expected))
  (error "C critical boundary ABI" label actual expected))
 (set! native-critical-check-count (+ native-critical-check-count 1)))
(define native-critical-test-unit (vector #f '#() '#()))
(define (native-critical-test-closure control?)
 (native-c-new-closure native-critical-test-unit
  (list 0 2 '() (bl-map (bl-key "arity") 0 (bl-key "native-control") control?)) '()))
(define native-critical-source (native-critical-test-closure #f))
(define native-critical-control (native-critical-test-closure #t))
(define (native-critical-test-machine closure)
 (vector native-critical-test-unit 0 (native-c-frame closure '()) '()
         bl-nil 0 0 '() #f bl-nil '() bl-nil
         seed-critical (native-c-source-boundary? closure)))

;; Non-tail Source return restores callee entry, then owner return restores
;; owner entry; the intermediate critical section belongs to the owner.
(set! seed-critical 0)
(let ((machine (native-critical-test-machine native-critical-source)))
 (set! seed-critical 1)
 (native-c-enter! machine native-critical-source '() 1 0 #f)
 (set! seed-critical 2)
 (native-c-return! machine bl-nil)
 (native-critical-check 'callee-return seed-critical 1)
 (native-c-return! machine bl-nil)
 (native-critical-check 'owner-return seed-critical 0))

;; An inline control can change critical depth, return, and continue in the
;; same Source function. Its physical return must not clean up the owner yet.
(let ((machine (native-critical-test-machine native-critical-source)))
 (set! seed-critical 1)
 (native-c-enter! machine native-critical-control '() 1 0 #f)
 (set! seed-critical 2)
 (native-c-return! machine bl-nil)
 (native-critical-check 'inline-return seed-critical 2)
 (native-c-return! machine bl-nil)
 (native-critical-check 'inline-owner-return seed-critical 0))

;; Tail loop/control replacement retains the owning Source cleanup boundary.
(let ((machine (native-critical-test-machine native-critical-source)))
 (set! seed-critical 1)
 (native-c-enter! machine native-critical-control '() 1 0 #t)
 (set! seed-critical 2)
 (native-c-return! machine bl-nil)
 (native-critical-check 'tail-control-owner seed-critical 0))

;; A genuine tail function replaces the entry depth at the actual tail edge.
(let ((machine (native-critical-test-machine native-critical-source)))
 (set! seed-critical 1)
 (native-c-enter! machine native-critical-source '() 1 0 #t)
 (set! seed-critical 2)
 (native-c-return! machine bl-nil)
 (native-critical-check 'tail-source-replacement seed-critical 1))

;; A nested protected-body driver does not itself leave the owning function.
;; A raise in that inline body retains its critical changes until the owner
;; eventually returns; a child Source unwind restores the child's entry.
(set! seed-critical 1)
(let ((machine (native-critical-test-machine native-critical-control)))
 (set! seed-critical 2)
 (native-c-unwind-critical! machine)
 (native-critical-check 'inline-catch-retains seed-critical 2))
(set! seed-critical 1)
(let ((machine (native-critical-test-machine native-critical-control)))
 (native-c-enter! machine native-critical-source '() 1 0 #f)
 (set! seed-critical 2)
 (native-c-unwind-critical! machine)
 (native-critical-check 'nested-callee-unwind seed-critical 1))

;; Catcher transports the exact exception object, after restoring the actual
;; Source scope. The fake step is only an ABI throw probe, no BL evaluation.
(set! seed-critical 0)
(let* ((sentinel (vector native-raise-marker (bl-key "throw")
                  (bl-key "exact-critical-exception") (bl-tuple (list '() '()))))
       (unit (vector (lambda (machine) (set! seed-critical 3) (raise sentinel)) '#() '#()))
       (source (native-c-new-closure unit
                 (list 0 2 '() (bl-map (bl-key "arity") 0 (bl-key "native-control") #f)) '()))
       (caught (with-exception-catcher (lambda (exception) exception)
                 (lambda () (native-c-invoke source '())))))
 (native-critical-check 'exception-identity (eq? caught sentinel) #t)
 (native-critical-check 'exception-source-cleanup seed-critical 0))
(display "NATIVE_C_CRITICAL_BOUNDARIES_PASS ")
(display native-critical-check-count) (newline)
