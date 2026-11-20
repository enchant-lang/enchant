;; Install the published expressions at their declared names and exercise a
;; transitive caller plus an independent definition in a fresh native process.
(with-exception-catcher
 (lambda (e) (display-exception e (current-error-port)) (exit 1))
 (lambda ()
  (let* ((arithmetic? (string=? "arithmetic" (getenv "BL_REPEAT_FIXTURE")))
         (names
          (if arithmetic?
           (append '("p-seed" "p-cost" "p-join")
            (let loop ((i 47) (out '()))
             (if (< i 0) out (loop (- i 1) (cons (string-append "p-row" (number->string i)) out)))))
           '("p-leaf" "p-mid" "p-main" "p-other")))
         (inputs (if arithmetic? '(2) '())))
   (call-with-input-file (getenv "BL_REPEAT_RESULT")
    (lambda (in)
     (for-each (lambda (name)
       (native-intern "repeat.demo" name (eval (read in) (interaction-environment)))) names)
     (if (not (eof-object? (read in))) (error "unexpected extra definitions"))))
   (display (bl-invoke (native-global "repeat.demo" (if arithmetic? "p-join" "p-main")) inputs))
   (display " ")
   (display (bl-invoke (native-global "repeat.demo" (if arithmetic? "p-row47" "p-other")) inputs))
   (newline) (exit 0))))
