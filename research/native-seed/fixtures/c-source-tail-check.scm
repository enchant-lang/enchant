;; Host frame/action ABI ONLY. Fixed Scheme step stand-ins below supply C
;; driver actions; no Source/ANF is decoded or used as an alternate body.
(define native-source-tail-checks 0)
(define (source-tail-check label actual expected)
 (if (not (bl-equal? actual expected))
  (error "C independent Source tail ABI" label actual expected))
 (set! native-source-tail-checks (+ native-source-tail-checks 1)))
(define source-tail-unit (vector #f '#() '#()))
(define (source-tail-frame name call)
 (bl-map (bl-key "fn") name (bl-key "arity") 0 (bl-key "call") call))
(define (source-tail-function name control? . unit)
 (native-c-new-closure (if (null? unit) source-tail-unit (car unit))
  (list 0 2 '() (bl-map (bl-key "fn") name (bl-key "arity") 0
                       (bl-key "native-control") control?)) '()))
(define source-tail-callee (source-tail-function "real-callee" #f))
(define (source-tail-machine frames site physical-tail?)
 (vector source-tail-unit 0 (vector '() bl-nil) '() bl-nil 1 0 '()
         physical-tail? bl-nil frames site seed-critical #t))
(define source-tail-bottom (source-tail-frame "bottom" (bl-key "direct")))
(set! seed-critical 0)

;; Internal runtime loops retain the authored display site, whose old :call
;; may say :direct. The actual internal :tail edge still elides every time.
(let* ((entry (source-tail-frame "authored-site" (bl-key "direct")))
       (frames (list entry source-tail-bottom))
       (site (bl-map (bl-key "fn") "internal-runtime" (bl-key "call") (bl-key "tail")
                     (bl-key "internal") #t))
       (machine (source-tail-machine frames site #t)))
 (let loop ((left 1024))
  (if (> left 0)
   (begin (native-c-apply-action machine source-tail-callee '()) (loop (- left 1)))))
 (source-tail-check 'internal-loop-bounded (length (vector-ref machine 10)) 2)
 (source-tail-check 'internal-keeps-authored-map (eq? (car (vector-ref machine 10)) entry) #t)
 (source-tail-check 'internal-keeps-ancestor
  (eq? (cadr (vector-ref machine 10)) source-tail-bottom) #t)
 (source-tail-check 'internal-physical-stack-bounded (length (vector-ref machine 3)) 0))

;; The converse matters: a protected direct edge cannot inherit :tail from
;; the preserved authored display map and accidentally retire its owner.
(let* ((entry (source-tail-frame "authored-tail-display" (bl-key "tail")))
       (frames (list entry source-tail-bottom))
       (site (bl-map (bl-key "call") (bl-key "direct") (bl-key "internal") #t))
       (machine (source-tail-machine frames site #t)))
 (native-c-apply-action machine source-tail-callee '())
 (source-tail-check 'internal-protected-retains-owner (length (vector-ref machine 10)) 3)
 (source-tail-check 'internal-protected-entry-preserved (eq? (car frames) entry) #t))

;; Physical tail is only the C continuation shape. Source says :direct here:
;; restore the caller entry BEFORE the real callee's logical frame is pushed.
(let* ((entry (source-tail-frame "caller-entry" (bl-key "tail")))
       (frames (list entry source-tail-bottom))
       (site (source-tail-frame "protected-site" (bl-key "direct")))
       (machine (source-tail-machine frames site #t)))
 (native-c-apply-action machine source-tail-callee '())
 (source-tail-check 'protected-real-push (length (vector-ref machine 10)) 3)
 (source-tail-check 'protected-callee-active-site
  (bl-get (car (vector-ref machine 10)) (bl-key "fn")) "protected-site")
 (source-tail-check 'protected-caller-restored-before-push (eq? (car frames) entry) #t))

;; Normal native completion restores at Source-direct physical-tail sites,
;; while the active site remains visible DURING the native invocation.
(let* ((entry (source-tail-frame "native-caller-entry" (bl-key "tail")))
       (frames (list entry source-tail-bottom))
       (site (source-tail-frame "protected-native-site" (bl-key "direct")))
       (machine (source-tail-machine frames site #t))
       (observed #f)
       (answer (native-c-apply-action machine
                 (lambda () (set! observed (car (native-logical-frames))) bl-nil) '())))
 (source-tail-check 'protected-native-return answer #t)
 (source-tail-check 'protected-native-active-site (bl-get observed (bl-key "fn")) "protected-native-site")
 (source-tail-check 'protected-native-entry-restored (eq? (car frames) entry) #t))

;; A genuine authored Source tail still replaces its owner.
(let* ((entry (source-tail-frame "old-direct-display" (bl-key "direct")))
       (frames (list entry source-tail-bottom))
       (site (source-tail-frame "authored-tail-site" (bl-key "tail")))
       (machine (source-tail-machine frames site #t)))
 (native-c-apply-action machine source-tail-callee '())
 (source-tail-check 'authored-tail-elides (length (vector-ref machine 10)) 2)
 (source-tail-check 'authored-tail-site
  (bl-get (car (vector-ref machine 10)) (bl-key "fn")) "authored-tail-site"))

;; A native leaf synchronously invokes a genuine C callback. That standalone
;; driver must not consume the pending outer call context or caller entry.
(let* ((entry (source-tail-frame "callback-caller-entry" (bl-key "direct")))
       (frames (list entry source-tail-bottom))
       (site (source-tail-frame "outer-native-active-site" (bl-key "direct")))
       (machine (source-tail-machine frames site #f))
       (callback-frames #f) (outer-during #f)
       (unit (vector (lambda (callback-machine)
                       (set! callback-frames (vector-ref callback-machine 10))
                       (set! outer-during (car frames))
                       (vector-set! callback-machine 4 bl-nil) 3) '#() '#()))
       (callback (source-tail-function "genuine-callback" #f unit)))
 (native-c-apply-action machine (lambda () (native-c-invoke callback '())) '())
 (source-tail-check 'callback-own-source
  (bl-get (car callback-frames) (bl-key "fn")) "genuine-callback")
 (source-tail-check 'callback-keeps-live-native-site
  (bl-get outer-during (bl-key "fn")) "outer-native-active-site")
 (source-tail-check 'callback-extra-real-source-frame (length callback-frames) 3)
 (source-tail-check 'callback-normal-native-restore (eq? (car frames) entry) #t))

;; Generated try controls remain inline even through standalone drivers. The
;; fence removes pending call metadata, not the enclosing live Source slots.
(let* ((entry (source-tail-frame "inline-owner-active" (bl-key "direct")))
       (prior (source-tail-frame "inline-owner-entry" (bl-key "direct")))
       (frames (list entry source-tail-bottom))
       (seen #f)
       (unit (vector (lambda (machine) (set! seen (vector-ref machine 10))
                        (vector-set! machine 4 (bl-key "inline-value")) 3) '#() '#()))
       (body (source-tail-function "generated-try-control" #t unit))
       (value
        (parameterize ((native-logical-frames frames)
                       (native-c-frame-call-context (vector frames prior #f)))
         (native-c-try body (lambda (kind reason trace) (error "unexpected handler")) #f))))
 (source-tail-check 'try-control-value value (bl-key "inline-value"))
 (source-tail-check 'try-control-no-frame (length seen) 2)
 (source-tail-check 'try-control-shares-owner (eq? seen frames) #t)
 (source-tail-check 'try-control-keeps-active-source (eq? (car frames) entry) #t))

(source-tail-check 'no-critical-leak seed-critical 0)
(display "NATIVE_C_SOURCE_TAIL_ABI_PASS ")
(display native-source-tail-checks) (newline)
