;; Late host entry routing avoids native.bootstrap <-> native.c-bootstrap
;; source dependency cycles. Every dispatched compiler body is compiled BL.
(define native-c-scheme-main native-main)
(set! native-main (lambda (arguments)
 (if (and (pair? arguments) (string=? (car arguments) "--compile-c"))
  (bl-invoke (native-global "native.c-bootstrap" "main") (list arguments))
  (native-c-scheme-main arguments))))

;; The explicit C profile replaces only the finite emission boundary. Reader,
;; expansion and canonical compilation remain the unchanged compiled BL path.
;; Resolve at call time: compiled units install their live Source definitions
;; after this host component. An absent C compiler/loader is a hard failure.
(define native-c-original-eval-node (native-leaf "host/eval-node/2"))
(if (not (eq? native-c-original-eval-node native-eval-node-scheme))
 (error "direct C profile requires the original finite Scheme emission boundary"))
(native-c-replace-leaf! "host/eval-node/2" native-c-original-eval-node
 (lambda (node context)
  (if (not (eq? native-c-backend (bl-key "c")))
   (error "direct C Source evaluation requires backend=c"))
  (if (or (not (procedure? native-c-eval-unit))
          (not (vector? native-c-toolchain))
          (not (= (vector-length native-c-toolchain) 3)))
   (error "direct C Source evaluation requires its actual configured dynamic loader"))
  (let ((emitter (native-global-exact "native.c-eval" "eval-node")))
   (if (not (native-c-closure? emitter))
    (error "direct C Source evaluation requires the captured C eval-node body"))
   (bl-invoke emitter (list node context))))
 2)
