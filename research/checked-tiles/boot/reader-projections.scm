(load (getenv "BOOT_OBSERVATIONS"))

(define (result mode source label)
 (if (string=? mode "spans")
  (with-exception-catcher
   (lambda (e) (list (bl-key "error") (native-exception-reason e)))
   (lambda () (list (bl-key "ok") (invoke (pick "read-source-spans") source label))))
  (observed mode source label)))

(with-exception-catcher
 (lambda (e) (display-exception e (current-error-port)) (exit 1))
 (lambda ()
  (let ((root (getenv "BOOT_OUT")))
   (for-each
    (lambda (job)
     (let* ((id (car job)) (mode (cadr job))
            (source (native-read-file (caddr job))) (label (list-ref job 3))
            (answer (result mode source label)))
      (call-with-output-file (string-append root "/" id ".wire")
       (lambda (p) (wire answer p)))
      (let loop ((trial 0))
       (when (< trial 5)
        (out "PROJECTION" id (timed (lambda () (result mode source label))))
        (loop (+ trial 1))))))
    (file-in (string-append root "/jobs.scm"))))
  (exit 0)))
