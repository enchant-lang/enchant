;; Load the four actual emitted expressions into an isolated native namespace,
;; then invoke the public caller and the unrelated definition.
(with-exception-catcher
 (lambda (e) (display-exception e (current-error-port)) (exit 1))
 (lambda ()
  (call-with-input-file (getenv "BL_REPEAT_RESULT")
   (lambda (in)
    (for-each (lambda (name)
     (native-intern "repeat.demo" name (eval (read in) (interaction-environment))))
     '("p-leaf" "p-mid" "p-main" "p-other"))
    (if (not (eof-object? (read in))) (error "unexpected extra definitions"))))
  (display (bl-invoke (native-global "repeat.demo" "p-main") '())) (display " ")
  (display (bl-invoke (native-global "repeat.demo" "p-other") '())) (newline) (exit 0)))
