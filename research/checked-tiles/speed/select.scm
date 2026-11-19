(define speed-general-serial (native-global-exact "speed.kernels" "serial"))
(define (speed-in-domain? n x)
  (and (fixnum? n) (<= 0 n 65535) (fixnum? x) (<= 0 x 65520)))
(native-intern "speed.kernels" "serial"
  (bl-register-callable!
    (lambda (n x)
      (if (speed-in-domain? n x) (speed-raw-serial n x) (speed-general-serial n x))) 2))
