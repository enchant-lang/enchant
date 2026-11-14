;; Native link unit only; append after host, values, leaves, and native-posix.
;; argv[1] is an immutable fixture shared library built from ffi-fixture.c.
(native-use-real-time!)
(let* ((library (native-library-open (car (native-command-line))))
       (start (h-now)) (job (native-ffi-submit library "bl_fixture_blocking" 200)))
 (if (native-ffi-ready? job) (error "blocking fixture finished before scheduler probe"))
 ;; Exercise an actor turn while the foreign worker owns its blocking call.
 (let ((ran? #f))
  (h-run-turn (h-make-frames (lambda () (set! ran? #t)) '()) 100)
  (if (not ran?) (error "blocking foreign call stopped actor progress")))
 (native-wait-fd (native-ffi-fd job) 2000)
 (if (not (native-ffi-ready? job)) (error "FFI worker completion was not ready"))
 (if (not (= (native-ffi-result job) 201)) (error "FFI result mismatch"))
 (if (< (- (h-now) start) 180) (error "monotonic wall clock did not observe blocking call"))
 (native-ffi-close job) (native-library-close library)
 (display "native POSIX clock/readiness/worker check passed") (newline))
