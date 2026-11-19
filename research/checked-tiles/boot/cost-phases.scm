;; Keep each phase's output as the next phase's input. Gambit's exec-stats
;; measures cumulative allocation, including temporary objects. Joining and
;; checking the output take place after the last measurement.
(define (cost-phase name thunk)
  (let ((stats (##exec-stats thunk)))
    (display "COST ")
    (display name)
    (for-each (lambda (key) (display " ") (display (cdr (assq key stats))))
              '(real-time user-time sys-time gc-real-time nb-gcs bytes-allocated))
    (newline)
    (cdr (assq 'result stats))))
(define (A-timed-round)
  (let* ((forms (cost-phase "read" A-read))
         (nodes (cost-phase "compile" (lambda () (A-compile-forms forms))))
         (texts (cost-phase "emit" (lambda () (A-emit-nodes nodes)))))
    (if (not (string=? (A-join texts) (native-read-file (string-append A-out "/native.scm"))))
        (error "timed compiler output differs"))))
