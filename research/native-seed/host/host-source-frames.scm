;; Optional Scheme source-call/tail ABI. No ANF interpretation: thunks are the
;; emitter's compiled Scheme functions. Keep emission off until the actor gate.
(define native-next-source-call (make-parameter #f))
(define native-source-tail-return (make-parameter #f))
(define native-source-tail-marker (list 'native-source-tail-marker))
(define native-source-value-marker (list 'native-source-value-marker))
(define (native-source-frame-list frames)
 (let loop ((xs frames) (left 64) (out '()))
  (if (or (= left 0) (null? xs)) (reverse out)
   (loop (cdr xs) (- left 1) (cons (car xs) out)))))
(define (bl-trace-frames trace)
 (if (and (bl-tag? trace 'tuple) (= (bl-count trace) 2)) (bl-nth trace 1) trace))
(define (native-source-trace)
 (bl-tuple (list '() (native-source-frame-list (native-logical-frames)))))
(set! native-capture-stack native-source-trace)
(define (native-source-protect thunk)
 (with-exception-catcher
  (lambda (e) (if (native-raised? e) (raise e)
   (native-raise (native-exception-kind e) (native-exception-reason e) (native-source-trace)))) thunk))
(set! bl-with-source-frame (lambda (own-frame thunk)
 (let* ((entry (native-next-source-call))
        (parent (if entry (vector-ref entry 1) (native-logical-frames)))
        (source (if entry (vector-ref entry 0) own-frame))
        (tail? (and entry (vector-ref entry 2)))
        (base (if (and tail? (pair? parent)) (cdr parent) parent))
        (frames (cons source base))
        (retire (native-source-tail-return)))
  ;; A tail callee replaces its caller at that caller's trampoline boundary.
  ;; Argument evaluation has finished, and protected try calls are non-tail.
  (if (and tail? retire)
   (retire (vector native-source-tail-marker frames thunk seed-critical))
   (let loop ((frames frames) (body thunk) (entry-critical seed-critical))
    (set! native-max-frames (max native-max-frames (length frames)))
    (let ((answer
     (call-with-current-continuation
      (lambda (return)
       (parameterize ((native-logical-frames frames)
                      (native-next-source-call #f)
                      (native-source-tail-return return))
        (with-exception-catcher
         (lambda (e)
          (set! seed-critical entry-critical)
          (if (native-raised? e) (raise e)
           (native-raise (native-exception-kind e) (native-exception-reason e) (native-source-trace))))
         (lambda ()
          (let ((value (body)))
           (set! seed-critical entry-critical)
           (vector native-source-value-marker value)))))))))
     (if (eq? (vector-ref answer 0) native-source-tail-marker)
      (loop (vector-ref answer 1) (vector-ref answer 2) (vector-ref answer 3))
      (vector-ref answer 1))))))))
(set! native-with-frame bl-with-source-frame)
(define (bl-source-call source tail? thunk)
 (let* ((parent (native-logical-frames))
        ;; Preserve caller source through generated actor runtime helpers,
        ;; using explicit emitter evidence exactly as JS's callSrc does.
        (source (if (and (bl-truthy (bl-get source (bl-key "internal") #f)) (pair? parent)) (car parent) source))
        (active (if (pair? parent)
                 ;; JS updates the live frame slot before invoking a callee.
                 ;; Preserve that site when an exception unwinds to a catch
                 ;; in THIS function; captured traces already copy their list.
                 (begin (set-car! parent source) parent)
                 (list source))))
  (parameterize ((native-logical-frames active)
                 (native-next-source-call (vector source parent tail?)))
   (native-source-protect thunk))))
;; Native leaves may synchronously invoke callbacks. Their callback is not the
;; callee of the pending BL call, so it must not inherit that call's tail jump.
;; Raw apply is an explicit forwarding boundary: preserve its call context
;; until native-raw-apply validates and reaches the actual target through bl-invoke.
(define native-invoke-without-source-context bl-invoke)
(set! bl-invoke (lambda (f xs)
 (let* ((call (native-resolve-call f xs)) (target (car call)) (arguments (cdr call)))
  (if (and (procedure? target) (not (eq? target native-raw-apply))
           (table-ref native-host-callables target #f))
   (parameterize ((native-next-source-call #f))
    (native-invoke-without-source-context target arguments))
   (native-invoke-without-source-context target arguments)))))
(set! h-logical-stack (lambda () (native-source-frame-list (native-logical-frames))))
;; New raises capture raw and normalized frames separately. Explicit re-raise
;; preserves its supplied raw trace bit for bit.
(set! h-exit (lambda (reason) (native-raise (bl-key "exit") reason (native-source-trace))))
(set! h-raise (lambda (reason) (native-raise (bl-key "error") (h-to-str reason) (native-source-trace))))
(set! native-throw (lambda (reason) (native-raise (bl-key "throw") reason (native-source-trace))))
;; Each actor turn owns an independent source stack; a suspended continuation
;; restores its own parameter chain when resumed, not the scheduler's chain.
(define native-run-turn-without-source-context h-run-turn)
(set! h-run-turn (lambda (frame budget)
 (let ((answer
  (parameterize ((native-logical-frames '()) (native-next-source-call #f) (native-source-tail-return #f))
   (native-run-turn-without-source-context frame budget))))
  (if (eq? (bl-get answer (bl-key "status")) (bl-key "error"))
   (bl-assoc answer (bl-key "frames") (bl-trace-frames (bl-get answer (bl-key "frames")))) answer))))

;; Explicit irreducible actor host functions; no source/namespace inference.
(for-each native-mark-host-callable! (list h-kw h-kw-name h-is-kw h-cons h-is-cons h-is-enil h-cons-head h-cons-tail h-is-list h-empty-list h-list->array h-tup h-is-tup h-tup-el h-tup-size h-struct h-is-struct h-struct-mod h-struct-field h-is-vec h-vec-size h-vec-el h-vec-append h-vec-remove h-vec-to-list h-vec-from-list h-is-set h-set-from-list h-set-put h-set-remove h-set-has h-set-size h-set-to-list h-bmap h-empty-map h-is-map h-map-get h-map-put h-map-remove h-map-keys h-map-size h-eq h-identical h-lt h-is-nil h-is-int h-is-float h-is-num h-is-str h-is-bool h-is-fn h-to-str h-describe h-arith h-str-cat h-str-size h-str-codepoints h-str-slice h-str-cmp h-truthy h-park h-wait-until h-now h-state h-set-state h-self h-set-self h-run-turn h-make-frames h-ref h-write h-emit h-raise h-max-frames h-logical-stack h-critical-enter h-critical-leave h-park-release h-record-error h-input-size h-take-input h-wait-input h-table-new h-table-lookup h-table-insert h-table-delete h-table-size h-table-destroy h-table-snapshot h-is-table h-ex-kind h-ex-reason h-ex-trace))
(define native-exception-trace-without-source-context native-exception-trace)
(set! native-exception-trace (lambda (exception)
 (if (native-raised? exception) (native-exception-trace-without-source-context exception) (native-source-trace))))
;; Rebind existing raw exception leaves to the source-aware capture operation;
;; a public duplicate registration still fails. Explicit raise/3 is unchanged.
(define (native-rebind-transport-leaf! key callable arity)
 (if (not (native-map-has? native-leaf-registry key)) (error "source ABI expected an existing transport leaf" key))
 (native-mark-host-callable! callable) (bl-register-callable! callable arity)
 (set! native-leaf-registry (bl-assoc native-leaf-registry key callable)))
(native-rebind-transport-leaf! "erlang/exit/1" h-exit 1)
(native-rebind-transport-leaf! "erlang/throw/1" native-throw 1)
(native-rebind-transport-leaf! "erlang/error/1"
 (lambda (reason) (native-raise (bl-key "error") reason (native-source-trace))) 1)
