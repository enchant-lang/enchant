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
   c#target-select! c#target-unselect!))
(with-exception-catcher
 (lambda (failure) (display-exception failure) (exit 1))
 (lambda ()
  (c#target-select! 'C '() #f)
  (if (not (procedure? c#target.dump)) (error "C target has no dump procedure"))
  (display "GVM_C_TARGET_DUMP_READY") (newline)
  (c#target-unselect!)))
(exit 0)
