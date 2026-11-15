;; Backend capability probe only: no authored BL/Scheme program is compiled.
(for-each
 (lambda (name)
  (with-exception-catcher
   (lambda (failure) (display "GVM_API_MISSING ") (write name) (newline) (exit 1))
   (lambda ()
    (if (not (procedure? (eval name))) (error "not a backend procedure" name))
    (display "GVM_API_PRESENT ") (write name) (newline))))
 '(c#make-proc-obj c#make-bbs c#make-bb c#make-frame
   c#make-label-entry c#make-copy c#make-jump c#make-c-intf
   c#target-select! c#target.dump c#target-unselect!))
(exit 0)
