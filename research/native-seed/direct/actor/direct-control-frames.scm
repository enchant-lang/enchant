;; Logical Source frames are distinct from the explicit C return stack.
;; Generated control functions keep exact callable arity metadata but add no
;; Source frame. Their local C tail returns still return to the host try/receive
;; barrier; emitted :call evidence alone decides logical caller elision.
(define native-c-source-stack-without-control native-c-source-stack)
(set! native-c-source-stack (lambda (closure previous physical-tail?)
 (let ((own (vector-ref closure 6)))
  (if (bl-truthy (bl-get own (bl-key "native-control") #f)) previous
   (let* ((incoming (if (pair? previous) (car previous) own))
          (logical-tail? (and physical-tail? (pair? previous)
                            (eq? (bl-get incoming (bl-key "call")) (bl-key "tail"))))
          (base (if logical-tail? (cdr previous) previous))
          (frames (cons incoming base)))
    (set! native-max-frames (max native-max-frames (length frames))) frames)))))
(define native-c-site-stack-without-control native-c-site-stack)
(set! native-c-site-stack (lambda (frames site)
 ;; Actor runtime call sites have explicit compiler evidence of being internal.
 ;; JS callSrc and the Scheme emitter preserve the incoming authored site.
 (if (and (not (bl-is-nil site)) (pair? frames)
          (bl-truthy (bl-get site (bl-key "internal") #f))) frames
  (native-c-site-stack-without-control frames site))))
