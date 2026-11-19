;; Both operands must be machine integers; standard Scheme arithmetic still
;; promotes overflow to an exact bignum. All other values use the native ABI.
(define (speed-add a b) (if (and (fixnum? a) (fixnum? b)) (+ a b) (native-arith-add a b)))
(define (speed-sub a b) (if (and (fixnum? a) (fixnum? b)) (- a b) (native-arith-sub a b)))
(define (speed-mul a b) (if (and (fixnum? a) (fixnum? b)) (* a b) (native-arith-mul a b)))
(define (speed-lt a b) (if (and (fixnum? a) (fixnum? b)) (< a b) (native-arith-lt a b)))
