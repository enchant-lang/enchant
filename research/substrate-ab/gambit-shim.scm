;; Gambit side of the observer shim. Paths are substituted by run-gambit.sh.
(define ab-source "@SOURCE@")
(define ab-bundle "@BUNDLE@")
(define ab-out "@OUT@")
(define ab-reps @REPS@)
(define (ab-now) (* 1000. (real-time)))
(define (ab-catch handler thunk) (with-exception-catcher handler thunk))
(define (ab-report e) (display-exception e) (newline) (force-output))
