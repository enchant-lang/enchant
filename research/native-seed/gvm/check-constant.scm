;; Load the compiled module passed as this driver's first argument.
;; This observer implements no authored program body or VM instruction.
(with-exception-catcher
 (lambda (failure) (display-exception failure) (exit 1))
 (lambda ()
  (load (car (reverse (command-line))))
  (let ((value (eval 'native-gvm-pilot/value)))
   (if (not (procedure? value)) (error "GVM export is not a native procedure"))
   (if (not (= (value) 42)) (error "GVM constant result differs"))
   (##gc)
   (if (not (= (value) 42)) (error "GVM procedure did not survive collection"))
   (display "NATIVE_GVM_CONSTANT_PASS 3") (newline)
   (exit 0))))
