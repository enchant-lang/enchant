(with-exception-catcher
 (lambda (e) (display-exception e (current-error-port)) (exit 1))
 (lambda ()
   (let ((module (getenv "BOOT_TRANSPORT")) (paths (call-with-input-file (getenv "BOOT_CONTROLS") read)))
     (define (observe reader path)
       (with-exception-catcher
         (lambda (e)
           (let* ((text (call-with-output-string "" (lambda (p) (display-exception e p))))
                  (port (open-input-string text)))
             ;; The rendered port identity varies across opens. Compare the actual
             ;; error headline and the operation reported by Gambit.
             (list 'error (read-line port) (and (error-exception? e) (error-exception-message e))
                   (with-exception-catcher (lambda (_) #f)
                     (lambda () (let ((prefix (read-char port))) (and (eqv? prefix #\() (read port))))))))
         (lambda () (list 'ok (reader path)))))
     (load module)
     (for-each
       (lambda (path)
         (let ((ref (observe native-read-file path)))
           (for-each
             (lambda (name reader)
               (let ((result (observe reader path)))
                 (write (list name path (car ref) (equal? ref result)
                        (if (eq? 'ok (car ref)) (string-length (cadr ref)) (cdr ref))
                        (if (eq? 'ok (car result)) (string-length (cadr result)) (cdr result))))
                 (newline)
                 (if (and (or (eq? 'ok (car ref)) (eq? name 'blocks)) (not (equal? ref result)))
                   (error "transport changed the required observation" name path))))
             '(bulk blocks) (list boot-bulk-read-file boot-block-read-file)))) paths)
     (exit 0))))
