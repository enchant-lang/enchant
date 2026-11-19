(define speed-general-serial (native-global-exact "speed.kernels" "serial"))
(define (speed-in-domain? n x)
  (and (fixnum? n) (<= 0 n 65535) (fixnum? x) (<= 0 x 65520)))
(native-intern "speed.kernels" "serial"
  (bl-register-callable!
    (lambda (n x)
      (cond ((not (speed-in-domain? n x)) (speed-general-serial n x))
            (seed-frame (speed-raw-serial n x))
            (else (speed-standalone-serial n x)))) 2))
