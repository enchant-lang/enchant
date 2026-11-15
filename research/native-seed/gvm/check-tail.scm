;; Observation only: original compiled host/core, actual loaded GVM module.
;; No authored function body, interpreter, direct C stepper, or hook override.
(with-exception-catcher
 (lambda (failure) (display-exception failure) (exit 1))
 (lambda ()
  (load (or (getenv "BL_GVM_PROBE_MODULE" #f) (error "missing explicit GVM module")))
  ;; Resolve one export symbol; no program body is evaluated here.
  (let ((tail (eval 'native-gvm-scalar/ds-tail (interaction-environment))))
   (if (not (procedure? tail)) (error "GVM ds-tail export is not a procedure"))
   (if (##interp-procedure? tail) (error "GVM ds-tail export is interpreted"))
   (if (not (= (bl-arithmetic ':add 17 25) 42)) (error "original native arithmetic bridge differs"))
   (let ((small (tail 2000 0)))
    (if (not (= small 2001000)) (error "GVM ds-tail2000 differs" small)))
   (##gc)
   (let* ((n @LARGE@) (start (time->seconds (current-time)))
          (large (tail n 0)) (seconds (- (time->seconds (current-time)) start))
          (expected (quotient (* n (+ n 1)) 2)))
    (if (not (= large expected)) (error "GVM larger native tail loop differs" n large expected))
    (display "NATIVE_GVM_TAIL_DIAGNOSTIC ")
    (write (list (cons 'n n) (cons 'result large) (cons 'seconds seconds)
                 (cons 'original-host #t) (cons 'interpreted-function #f)))
    (newline))
   (display "NATIVE_GVM_HOST_TAIL_PASS 5") (newline) (force-output)
   (exit 0))))
;; Exact original bundle DATA follows; exit above prevents macro bootstrap.
