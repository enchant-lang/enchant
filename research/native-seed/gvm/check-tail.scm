;; Observer only. The function body is the original BL function in the loaded
;; native GVM module. Run in the qualified compiled host before macro loading.
(with-exception-catcher
 (lambda (failure) (display-exception failure) (exit 1))
 (lambda ()
  (load (or (getenv "BL_GVM_PROBE_MODULE" #f) (error "missing explicit GVM module")))
  (let ((f (eval 'native-gvm-scalar/ds-tail)))
   (if (not (procedure? f)) (error "tail export is not a native procedure"))
   (for-each
    (lambda (row)
     (if (not (= (f (car row) 0) (cadr row))) (error "native GVM tail result differs" row)))
    '((0 0) (2000 2001000) (100000 5000050000)))
   (##gc)
   (if (not (= (f 2000 0) 2001000)) (error "tail function differs after GC"))
   (display "NATIVE_GVM_TAIL_PASS 5") (newline) (force-output)
   (exit 0))))
