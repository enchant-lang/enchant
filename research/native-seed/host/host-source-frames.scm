;; Source frames from static site descriptors (N4). Debug emission adds plain
;; statements around calls, never a wrapper: no thunk, continuation, exception
;; catcher or parameter per call, and a BL tail call stays a Scheme tail call.
;;   (bl-source-enter SITE)            first statement of a function body
;;   (bl-source-call SITE) -> entry    before a non-tail call, then
;;   (bl-source-return entry VALUE)    when that call returns normally
;;   (bl-source-tail SITE)             before a tail call
;; SITE is the emission-table entry: a constant vector #(internal? key value …)
;; written into the code, turned into a frame map only when a stack is
;; observed (h-logical-stack, a raise). A site whose map holds a value with no
;; Scheme datum is #(internal? builder) instead.
;;
;; State (defined in host-values.scm): native-source-frames, the logical stack
;; as a list of mutable records #(site critical depth), innermost first; and
;; native-source-pending, the call whose callee has not entered yet. Pending is
;; not consumed by an entry: until the call site restores it, every BL entry
;; that is not preceded by its own call site (callbacks from host leaves and
;; from release code) is a callee of that site, as before.
;;
;; Dynamic extent is restored explicitly where the old parameters unwound:
;; non-tail call return (caller side), host-callable calls, bl-try catches,
;; bl-guard, actor park/resume and whole turns. A frame's critical depth at
;; entry is restored when it completes or unwinds, as JS's per-frame cds do.
(define (bl-trace-frames trace)
 (if (and (bl-tag? trace 'tuple) (= (bl-count trace) 2)) (bl-nth trace 1) trace))
(define (bl-source-site-frame site)
 (if (and (= (vector-length site) 2) (procedure? (vector-ref site 1))) ((vector-ref site 1))
  (let loop ((i (- (vector-length site) 1)) (pairs '()))
   (if (< i 1) (apply bl-map pairs)
    (loop (- i 1) (cons (let ((v (vector-ref site i))) (if (eq? v (void)) bl-nil v)) pairs))))))
(define (native-source-frame-list frames)
 (let loop ((xs frames) (left 64) (out '()))
  (if (or (= left 0) (null? xs)) (reverse out)
   (loop (cdr xs) (- left 1) (cons (bl-source-site-frame (vector-ref (car xs) 0)) out)))))
(define (native-source-trace)
 (bl-tuple (list '() (native-source-frame-list native-source-frames))))
(set! native-capture-stack native-source-trace)
(define (native-source-record site base)
 (vector site seed-critical (+ 1 (if (pair? base) (vector-ref (car base) 2) 0))))

;; A call site. The live frame points at THIS call while it runs (a raise there
;; is reported at the call); the entry remembers what to restore.
;; entry = #(source parent tail? caller-source pending-before active)
(define (native-source-site site tail?)
 (let* ((parent native-source-frames)
        (caller (and (pair? parent) (vector-ref (car parent) 0)))
        ;; Generated actor runtime helpers keep their caller's source.
        (source (if (and (vector-ref site 0) (pair? parent)) caller site))
        (active (if (pair? parent)
                 (begin (vector-set! (car parent) 0 source) parent)
                 (list (native-source-record source '()))))
        (entry (vector source parent tail? caller native-source-pending active)))
  (set! native-source-frames active)
  (set! native-source-pending entry)
  entry))
(define (bl-source-call site) (native-source-site site #f))
(define (bl-source-tail site) (native-source-site site #t))
(define (bl-source-return entry value)
 (let ((parent (vector-ref entry 1)))
  ;; A BL callee replaced the stack: its frame (the last of a tail chain)
  ;; completes now and restores its entry critical depth.
  (if (and (pair? native-source-frames) (not (eq? native-source-frames (vector-ref entry 5))))
   (set! seed-critical (vector-ref (car native-source-frames) 1)))
  ;; The caller resumes at its previous entry site.
  (if (pair? parent) (vector-set! (car parent) 0 (vector-ref entry 3)))
  (set! native-source-frames parent)
  (set! native-source-pending (vector-ref entry 4))
  value))
;; A function entry. A non-tail callee gets the call site in its OWN new frame
;; and its caller goes back to its entry site (JS's srcs[caller] restoration);
;; a tail callee replaces its caller. With no pending site (or a host marker,
;; whose source slot is #f) the function pushes its own site.
(define (bl-source-enter own)
 (let* ((entry native-source-pending)
        (parent (if entry (vector-ref entry 1) native-source-frames))
        (site? (and entry (vector-ref entry 0) #t))
        (tail? (and site? (vector-ref entry 2)))
        (source (if site? (vector-ref entry 0) own)))
  (if (and site? (not tail?) (pair? parent)) (vector-set! (car parent) 0 (vector-ref entry 3)))
  (let* ((base (if (and tail? (pair? parent)) (cdr parent) parent))
         (record (native-source-record source base)))
   (if (> (vector-ref record 2) native-max-frames) (set! native-max-frames (vector-ref record 2)))
   (set! native-source-frames (cons record base)))))
;; Unwind to `frames` after a raise (or a guard): the outermost record popped
;; restores its entry critical depth, as each popped JS frame does in turn.
(define (native-source-unwind! frames)
 (let loop ((xs native-source-frames) (popped #f))
  (if (or (eq? xs frames) (not (pair? xs)))
   (begin (if popped (set! seed-critical (vector-ref (car popped) 1)))
          (set! native-source-frames frames))
   (loop (cdr xs) xs))))

;; Native leaves may synchronously invoke callbacks. Their callback is not the
;; callee of the pending BL call, so a host-callable call installs a host
;; marker: callbacks push their own frame onto the leaf's caller stack.
;; Raw apply is an explicit forwarding boundary: its target keeps the call.
(define native-invoke-without-source-context bl-invoke)
(set! bl-invoke (lambda (f xs)
 (let* ((call (native-resolve-call f xs)) (target (car call)) (arguments (cdr call)))
  (if (and (procedure? target) (not (eq? target native-raw-apply))
           (table-ref native-host-callables target #f))
   (let ((pending native-source-pending))
    (set! native-source-pending (vector #f native-source-frames #f #f #f #f))
    (let ((answer (native-invoke-without-source-context target arguments)))
     (set! native-source-pending pending)
     answer))
   (native-invoke-without-source-context target arguments)))))
;; A catch resumes in the function that wrote the try: its stack, with the
;; raising call site still live (the trace was taken from it first).
(define native-try-without-source-context bl-try)
(set! bl-try (lambda (body handler after)
 (let ((frames native-source-frames) (pending native-source-pending))
  (native-try-without-source-context body
   (lambda (kind reason trace)
    (native-source-unwind! frames) (set! native-source-pending pending)
    (handler kind reason trace))
   after))))
;; Guards are emitted without sites; a BL call in one is not a callee of the
;; enclosing call. Any exception is false, so the stack is restored both ways.
(define native-guard-without-source-context bl-guard)
(set! bl-guard (lambda (thunk)
 (let ((frames native-source-frames) (pending native-source-pending))
  (set! native-source-pending #f)
  (let ((answer (native-guard-without-source-context thunk)))
   (native-source-unwind! frames) (set! native-source-pending pending)
   answer))))
(set! h-logical-stack (lambda () (native-source-frame-list native-source-frames)))
;; New raises capture raw and normalized frames separately. Explicit re-raise
;; preserves its supplied raw trace bit for bit.
(set! h-exit (lambda (reason) (native-raise (bl-key "exit") reason (native-source-trace))))
(set! h-raise (lambda (reason) (native-raise (bl-key "error") (h-to-str reason) (native-source-trace))))
(set! native-throw (lambda (reason) (native-raise (bl-key "throw") reason (native-source-trace))))
;; A parked actor resumes with its own stack, not the scheduler's.
(define native-park-without-source-context h-park)
(set! h-park (lambda (status)
 (let ((frames native-source-frames) (pending native-source-pending))
  (let ((answer (native-park-without-source-context status)))
   (set! native-source-frames frames) (set! native-source-pending pending)
   answer))))
;; Each actor turn starts an independent source stack and gives the
;; scheduler's back when it returns, whatever the turn's status.
(define native-run-turn-without-source-context h-run-turn)
(set! h-run-turn (lambda (frame budget)
 (let ((frames native-source-frames) (pending native-source-pending))
  (set! native-source-frames '()) (set! native-source-pending #f)
  (let ((answer (native-run-turn-without-source-context frame budget)))
   (set! native-source-frames frames) (set! native-source-pending pending)
   (if (eq? (bl-get answer (bl-key "status")) (bl-key "error"))
    (bl-assoc answer (bl-key "frames") (bl-trace-frames (bl-get answer (bl-key "frames")))) answer)))))

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
 (native-replace-leaf! key callable))
(native-rebind-transport-leaf! "erlang/exit/1" h-exit 1)
(native-rebind-transport-leaf! "erlang/throw/1" native-throw 1)
(native-rebind-transport-leaf! "erlang/error/1"
 (lambda (reason) (native-raise (bl-key "error") reason (native-source-trace))) 1)
