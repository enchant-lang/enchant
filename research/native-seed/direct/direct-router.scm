;; Late host entry routing avoids native.bootstrap <-> native.c-bootstrap
;; source dependency cycles. Every dispatched compiler body is compiled BL.
(define native-c-scheme-main native-main)
(set! native-main (lambda (arguments)
 (if (and (pair? arguments) (string=? (car arguments) "--compile-c"))
  (bl-invoke (native-global "native.c-bootstrap" "main") (list arguments))
  (native-c-scheme-main arguments))))
