;; Time the outermost activation of ONE selected fixed-arity BL entry.
;; Count its recursive calls, but charge their elapsed time only once.
(define (boundary-clock phase name cell action expected)
 (let* ((var (##make-global-var (string->symbol cell)))
        (original (##global-var-ref var)) (active #f) (elapsed 0.) (calls 0))
  (##global-var-set! var
   (lambda args
    (set! calls (+ calls 1))
    (if active (apply original args)
     (let ((start (real-time)))
      (set! active #t)
      (let ((value (apply original args)))
       (set! active #f)
       (set! elapsed (+ elapsed (- (real-time) start)))
       value)))))
  (let* ((start (real-time)) (value (action)) (duration (- (real-time) start)))
   (##global-var-set! var original)
   (if (not (equal? expected value)) (error "instrumented phase result differs" phase name))
   (display "BOUND ") (display phase) (display " ") (display name)
   (display " ") (display calls) (display " ") (display (* 1000 elapsed))
   (display " ") (display (* 1000 duration)) (newline))))
