;; Logical Source slots follow JS runTurn: make the call site live during
;; resolution/native invocation; restore the caller entry before a successful
;; NONTAIL BL push and after successful NONTAIL native completion. Exceptions
;; retain their active site. Physical C return slots remain a separate ABI.
(define native-c-frame-call-context (make-parameter #f))
(define (native-c-frame-snapshot frames)
 (let loop ((xs frames) (out '()))
  (if (null? xs) (reverse out) (loop (cdr xs) (cons (car xs) out)))))
;; Once live frame slots are mutable, exported/captured frame lists must be
;; snapshots. The actor source addon later supplies its existing capped view.
(set! h-logical-stack (lambda () (native-c-frame-snapshot (native-logical-frames))))
(native-mark-host-callable! h-logical-stack)
(bl-register-callable! h-logical-stack 0)

(define native-c-source-stack-without-control native-c-source-stack)
(set! native-c-source-stack (lambda (closure previous physical-tail?)
 (let* ((own (vector-ref closure 6))
        (context (native-c-frame-call-context))
        (matching? (and context (eq? previous (vector-ref context 0))))
        (incoming (if (pair? previous) (car previous) own)))
  (cond
   ;; Unit roots have no Source metadata. Delegate exactly to the existing
   ;; nil-source rule, including its physical-tail base behavior.
   ((bl-is-nil own)
    (native-c-source-stack-without-control closure previous physical-tail?))
   ((bl-truthy (bl-get own (bl-key "native-control") #f))
    ;; Generated loop/try/receive controls are inline Source destinations.
    ;; Undo their synthetic call site; no Source frame is pushed or popped.
    (if (and matching? (pair? previous)) (set-car! previous (vector-ref context 1)))
    previous)
   (else
    (let* ((logical-tail? (and physical-tail? (pair? previous)
                               (eq? (bl-get incoming (bl-key "call")) (bl-key "tail"))))
           (base (if logical-tail? (cdr previous) previous)))
     (if (and matching? (not physical-tail?) (pair? previous))
      (set-car! previous (vector-ref context 1)))
     (let ((frames (cons incoming base)))
      (set! native-max-frames (max native-max-frames (length frames))) frames)))))))

(set! native-c-site-stack (lambda (frames site)
 (if (or (bl-is-nil site) (null? frames)) frames
  (if (bl-truthy (bl-get site (bl-key "internal") #f)) frames
   (let ((top (car frames)))
    (for-each (lambda (key) (set! top (bl-assoc top key (bl-get site key)))) (h-map-keys site))
    ;; Keep the owning slot live across a caught raise. Trace snapshots copied
    ;; above cannot be changed by a later call or frame restoration.
    (set-car! frames top) frames)))))

(define native-c-apply-action-without-frame-slots native-c-apply-action)
(set! native-c-apply-action (lambda (machine callee arguments)
 (let* ((frames (vector-ref machine 10))
        (site (vector-ref machine 11))
        (tail? (vector-ref machine 8))
        (caller (if (pair? frames) (car frames) #f))
        (context (if (and (not (bl-is-nil site)) (pair? frames)) (vector frames caller) #f)))
  (parameterize ((native-c-frame-call-context context))
   (let ((answer (native-c-apply-action-without-frame-slots machine callee arguments)))
    ;; Do this only on normal completion. A C BL callee already restored its
    ;; caller slot while constructing its own Source frame above. Native leaves
    ;; restore here. Synthetic services carry no Source call site to restore.
    (if (and context (not tail?)) (set-car! frames caller))
    answer)))))
