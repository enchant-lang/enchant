;; Value/control services for direct C, not an ANF/source evaluator. The only
;; program decisions are C-emitted pc edges and closure entries. The driver
;; owns allocation/GC roots and performs an action AFTER the C stack returns.
(define native-c-action-abi 2)
(define (native-c-require-action-abi! requested)
 (if (not (and (integer? requested) (exact? requested) (= requested native-c-action-abi)))
  (error "direct C action ABI mismatch" requested native-c-action-abi)) bl-nil)
(define (native-c-require-pure-bif-abi! requested)
 (if (not (eqv? requested 1)) (error "direct C pure BIF feature mismatch" requested)) bl-nil)
;; Private physical machine fields only: every call site below uses a literal
;; slot0..13 in a constructed ABI2 machine of length14/15. Evaluate expressions
;; under the caller's SAFE declarations before the single unchecked access.
;; Never use these macros for Source values, closure metadata or frame indices.
(define-macro (native-c-machine-ref machine index)
 (if (not (and (integer? index) (exact? index) (<= 0 index) (<= index 13)))
  (error "private C machine access requires a fixed ABI slot0..13" index))
 (let ((object (gensym)))
  `(let ((,object ,machine))
    (let () (declare (not safe)) (vector-ref ,object ,index)))))
(define-macro (native-c-machine-set! machine index value)
 (if (not (and (integer? index) (exact? index) (<= 0 index) (<= index 13)))
  (error "private C machine update requires a fixed ABI slot0..13" index))
 (let ((object (gensym)) (incoming (gensym)))
  `(let* ((,object ,machine) (,incoming ,value))
    (let () (declare (not safe)) (vector-set! ,object ,index ,incoming)))))

(define native-c-closure-marker (list 'native-c-closure-marker-v1))
(define native-c-step-count 0)
(define native-c-gc-between-steps? #f)
(define native-c-forced-gc-count 0)
(define native-c-gc-interval
 (let ((text (getenv "BL_NATIVE_C_GC_INTERVAL" #f)))
  (if (not text) 0
   (let ((n (string->number text)))
    (if (not (and (integer? n) (exact? n) (> n 0)))
     (error "BL_NATIVE_C_GC_INTERVAL requires a positive exact integer")) n))))
(define (native-c-after-step!)
 (set! native-c-step-count (+ native-c-step-count 1))
 (if (or native-c-gc-between-steps?
         (and (> native-c-gc-interval 0) (= (modulo native-c-step-count native-c-gc-interval) 0)))
  (begin (##gc) (set! native-c-forced-gc-count (+ native-c-forced-gc-count 1)))))
;; Disabled for an arbitrary host. Only a producer that has admitted the exact
;; frozen stock host may opt in after assembling the complete addon stack.
(define native-c-noactor-tick-enabled? #f)
(define native-c-noactor-ticks-elided 0)
;; The late, independently guarded primitive installer owns these hooks.
(define native-c-pure-bif-enabled? #f)
(define (native-c-refresh-pure-bifs! machine) #f)
(define (native-c-record-pure-bifs! machine) #f)
(define (native-c-new-extension) (vector 1 0 0 '#() 0))
(define native-c-noactor-tick-allowed?
 (let ((stock-tick h-tick) (stock-after-step native-c-after-step!)
       (stock-frames native-logical-frames))
  (lambda ()
   (and native-c-noactor-tick-enabled?
        (not seed-frame)
        (eq? h-tick stock-tick)
        (eq? native-c-after-step! stock-after-step)
        (eq? native-logical-frames stock-frames)
        (not native-c-gc-between-steps?)
        (eqv? native-c-gc-interval 0)))))

;; Optional machine extension V1: field0=version, field1=tick state.
;; The other fields belong to independently gated direct-machine services.
(define (native-c-tick-extension machine)
 (and (= (vector-length machine) 15)
  (let ((extension (vector-ref machine 14)))
   (and (vector? extension) (>= (vector-length extension) 5)
        (eqv? (vector-ref extension 0) 1) extension))))
;; Emission constructs the C step ONCE, stores it live at unit0 and
;; retains its owned identity at unit4. A profiling wrapper may change
;; scheduler state before forwarding: it must never receive permission.
(define (native-c-owned-step? machine)
 (let ((unit (vector-ref machine 0)))
  (and (vector? unit) (= (vector-length unit) 5)
       (procedure? (vector-ref unit 0))
       (eq? (vector-ref unit 0) (vector-ref unit 4)))))
(define (native-c-prepare-noactor-tick! machine)
 (let ((extension (native-c-tick-extension machine)))
  (if extension
   (vector-set! extension 1
    (if (and (native-c-noactor-tick-allowed?) (native-c-owned-step? machine)) 1 0)))))
(define (native-c-record-noactor-tick! machine)
 (let ((extension (native-c-tick-extension machine)))
  (if extension
   (let ((skipped? (eqv? (vector-ref extension 1) 2)))
    ;; No eligibility is retained across an arbitrary Scheme callback/hook.
    (vector-set! extension 1 0)
    (if skipped?
     (set! native-c-noactor-ticks-elided (+ native-c-noactor-ticks-elided 1)))))))

(define (native-c-caught-frames trace)
 ;; The compiler's normalized __STACKTRACE__ list is distinct from the raw
 ;; {(),frames} envelope passed verbatim to an explicit re-raise.
 (if (and (bl-tag? trace 'tuple) (= (bl-count trace) 2)) (bl-nth trace 1) trace))
(define native-c-recursion-marker (list 'native-c-recursion-marker))
(define (native-c-new-recursion-cell) (vector native-c-recursion-marker #f))
(define (native-c-recursion-cell? value)
 (and (vector? value) (= (vector-length value) 2)
      (eq? (vector-ref value 0) native-c-recursion-marker)))
(define (native-c-recursion-ref cell)
 (if (not (and (native-c-recursion-cell? cell) (vector-ref cell 1)))
  (error "direct C recursive function used before initialization"))
 (vector-ref cell 1))
(define (native-c-fill-recursion! cell value)
 (if (not (and (native-c-recursion-cell? cell) (not (vector-ref cell 1))
               (or (native-c-closure? value) (native-multi-callable? value))))
  (error "direct C recursive function initialization contract"))
 (vector-set! cell 1 value) value)
(for-each (lambda (entry)
 (native-mark-host-callable! (car entry)) (bl-register-callable! (car entry) (cdr entry)))
 (list (cons native-c-new-recursion-cell 0) (cons native-c-recursion-ref 1)
       (cons native-c-fill-recursion! 2) (cons native-c-caught-frames 1)))
(define (native-c-closure? v)
 (and (vector? v) (= (vector-length v) 7)
      (eq? (vector-ref v 0) native-c-closure-marker)))
(define native-c-host-is-fn h-is-fn)
(set! h-is-fn (lambda (v) (or (native-c-closure? v) (native-c-host-is-fn v))))
(define native-c-host-accepts? native-callable-accepts?)
(set! native-callable-accepts? (lambda (f n)
 (if (native-c-closure? f)
  (and (h-is-int n) (>= n 0) (= n (bl-get (vector-ref f 6) (bl-key "arity"))))
  (native-c-host-accepts? f n))))
;; C descriptors are this backend's raw function values. Preserve the original
;; Erlang predicates for all OTHER values, especially $blfn tuples: a language
;; dispatcher is callable but is not an Erlang fun. Capture the exact registered
;; leaves so this extension follows the same raw-function ABI as the value host.
(define native-c-original-is-function1 (native-remote "erlang/is_function/1"))
(define native-c-original-is-function2 (native-remote "erlang/is_function/2"))
(define (native-c-replace-leaf! key original replacement arity)
 ;; Backend installation is an explicit replacement, not ordinary duplicate
 ;; registration. Refuse a stale captured entry before mutating the registry.
 (if (not (eq? (native-leaf key) original))
  (error "direct C backend leaf changed before checked replacement" key))
 (if (not (procedure? replacement)) (error "direct C replacement is not a host procedure" key))
 (native-check-function-arity arity)
 (native-mark-host-callable! replacement)
 (bl-register-callable! replacement arity)
 (set! native-leaf-registry (bl-assoc native-leaf-registry key replacement)) replacement)
(native-c-replace-leaf! "erlang/is_function/1" native-c-original-is-function1 (lambda (f)
 (if (native-c-closure? f) #t (native-c-original-is-function1 f)))
 1)
(native-c-replace-leaf! "erlang/is_function/2" native-c-original-is-function2 (lambda (f n)
 (native-check-function-arity n)
 (if (native-c-closure? f)
  (native-callable-accepts? f n) (native-c-original-is-function2 f n)))
 2)
(define native-c-original-apply2 (native-remote "erlang/apply/2"))
(define (native-c-check-raw-apply! function arguments)
 (if (not (native-list? arguments))
  (native-raise (bl-key "error") (bl-key "badarg") (native-capture-stack)))
 (if (not (or (native-c-closure? function) (procedure? function)))
  (native-raise (bl-key "error") (bl-tuple (list (bl-key "badfun") function)) (native-capture-stack)))
 (if (and (native-c-closure? function)
          (not (native-callable-accepts? function (length arguments))))
  (native-raise (bl-key "error")
   (bl-tuple (list (bl-key "badarity") (bl-tuple (list function arguments)))) (native-capture-stack))))
(define native-c-raw-apply2
 (native-c-replace-leaf! "erlang/apply/2" native-c-original-apply2
  (lambda (function arguments)
   (native-c-check-raw-apply! function arguments)
   (if (native-c-closure? function) (native-c-invoke function arguments)
    (native-c-original-apply2 function arguments))) 2))
(define (native-c-resolve-call callee arguments)
 ;; Raw apply of a C fun enters the SAME explicit machine stack. A Scheme
 ;; wrapper invocation here would nest trampolines on each tail-recursive
 ;; erlang:apply/2 call, despite the emitted C tail edge.
 (let* ((plan (native-resolve-call callee arguments)) (target (car plan)) (args (cdr plan)))
  (if (and (eq? target native-c-raw-apply2) (pair? args) (pair? (cdr args))
           (null? (cddr args)) (native-c-closure? (car args)))
   (begin (native-c-check-raw-apply! (car args) (cadr args)) (cons (car args) (cadr args)))
   plan)))
(define (native-c-new-closure unit metadata captures)
 ;; metadata = (entry frame-size capture-destinations source-frame)
 (vector native-c-closure-marker unit (car metadata) (cadr metadata)
         captures (caddr metadata) (cadddr metadata)))
(define (native-c-slots frame slots) (map (lambda (i) (vector-ref frame i)) slots))
;; A frame is private rooted storage. Closure captures are VALUE lists made by
;; native-c-slots, not a reference to this vector. Snapshot the descriptor
;; fields before clearing; the argument/capture/destination spines cannot alias
;; the frame through the opaque C ABI.
(define (native-c-fill-frame! frame arguments destinations captures)
 (vector-set! frame 0 arguments)
 (for-each (lambda (destination value) (vector-set! frame destination value))
           destinations captures)
 frame)
(define (native-c-frame closure args)
 (native-c-fill-frame! (make-vector (vector-ref closure 3) bl-nil) args
                      (vector-ref closure 5) (vector-ref closure 4)))
(define (native-c-tail-frame frame closure arguments)
 (let ((required (vector-ref closure 3))
       (destinations (vector-ref closure 5))
       (captures (vector-ref closure 4)))
  (if (< (vector-length frame) required)
   (native-c-frame closure arguments)
   (begin
    ;; Clear the FULL old capacity, including slots beyond the new function's
    ;; declared size: unused old roots must not retain previous activations.
    (vector-fill! frame bl-nil)
    (native-c-fill-frame! frame arguments destinations captures)))))
(define (native-c-source-stack closure previous tail?)
 (let* ((source (vector-ref closure 6))
        (base (if (and tail? (pair? previous)) (cdr previous) previous))
        (frames (if (bl-is-nil source) base (cons source base))))
  (set! native-max-frames (max native-max-frames (length frames))) frames))
;; Physical C continuations and Source function boundaries are distinct.
;; Generated loop/try/receive controls are inline; they introduce no critical
;; scope. A tail control keeps the owning function's scope alive until return.
;; Machine slots 12/13 are the entry depth and ownership of its current scope.
(define (native-c-source-boundary? closure)
 (let ((source (vector-ref closure 6)))
  (and (not (bl-is-nil source))
       (not (bl-truthy (bl-get source (bl-key "native-control") #f))))))
(define (native-c-unwind-critical! machine)
 ;; A nested control driver may catch inside its owning Source function.
 ;; Restore only genuine functions traversed by this unwind; an inline body
 ;; that raises without leaving a Source function retains its current depth.
 (if (native-c-machine-ref machine 13) (set! seed-critical (native-c-machine-ref machine 12)))
 (for-each (lambda (caller)
  (if (vector-ref caller 6) (set! seed-critical (vector-ref caller 5))))
  (native-c-machine-ref machine 3)))
(define (native-c-enter! machine callee args destination next tail?)
 (if (not tail?)
  (native-c-machine-set! machine 3
   (cons (vector (native-c-machine-ref machine 0) next (native-c-machine-ref machine 2) destination
                  (native-c-machine-ref machine 10) (native-c-machine-ref machine 12)
                  (native-c-machine-ref machine 13)) (native-c-machine-ref machine 3))))
 (cond
  ((native-c-source-boundary? callee)
   ;; A genuine tail callee replaces the old entry base, exactly as JS cds.
   (native-c-machine-set! machine 12 seed-critical) (native-c-machine-set! machine 13 #t))
  ((not tail?)
   ;; Non-tail controls return to a separately saved owning continuation.
   (native-c-machine-set! machine 12 seed-critical) (native-c-machine-set! machine 13 #f)))
 (native-c-machine-set! machine 10 (native-c-source-stack callee (native-c-machine-ref machine 10) tail?))
 (native-c-machine-set! machine 0 (vector-ref callee 1))
 (native-c-machine-set! machine 1 (vector-ref callee 2))
 (native-c-machine-set! machine 2
  (if tail? (native-c-tail-frame (native-c-machine-ref machine 2) callee args)
   (native-c-frame callee args))))
(define (native-c-return! machine value)
 (if (native-c-machine-ref machine 13) (set! seed-critical (native-c-machine-ref machine 12)))
 (if (null? (native-c-machine-ref machine 3))
  (begin (native-c-machine-set! machine 9 value) #t)
  (let ((caller (car (native-c-machine-ref machine 3))))
   (native-c-machine-set! machine 3 (cdr (native-c-machine-ref machine 3)))
   (native-c-machine-set! machine 0 (vector-ref caller 0))
   (native-c-machine-set! machine 1 (vector-ref caller 1))
   (native-c-machine-set! machine 2 (vector-ref caller 2))
   (native-c-machine-set! machine 10 (vector-ref caller 4))
   (native-c-machine-set! machine 12 (vector-ref caller 5))
   (native-c-machine-set! machine 13 (vector-ref caller 6))
   (vector-set! (vector-ref caller 2) (vector-ref caller 3) value) #f)))
(define native-c-fallback-invoke bl-invoke)
(define (native-c-site-stack frames site)
 (if (or (bl-is-nil site) (null? frames)) frames
  (let ((top (car frames)))
   (for-each (lambda (key) (set! top (bl-assoc top key (bl-get site key)))) (h-map-keys site))
   (cons top (cdr frames)))))
;; Remains disabled until the complete standard planner stack is installed.
;; The late guard proves that a genuine procedure's target/args are unchanged.
(define native-c-direct-procedure? (lambda (callee) #f))
(define (native-c-apply-action machine callee args)
 (let* ((frames (native-c-site-stack (native-c-machine-ref machine 10) (native-c-machine-ref machine 11)))
        (direct? (native-c-direct-procedure? callee))
        (plan (if direct? #f
               (parameterize ((native-logical-frames frames)) (native-c-resolve-call callee args))))
        (callee (if direct? callee (car plan))) (args (if direct? args (cdr plan)))
        (destination (native-c-machine-ref machine 5)) (next (native-c-machine-ref machine 6))
        (tail? (native-c-machine-ref machine 8)))
  (native-c-machine-set! machine 10 frames)
  (if (native-c-closure? callee)
   (begin (native-c-enter! machine callee args destination next tail?) #f)
   (let ((value (parameterize ((native-logical-frames (native-c-machine-ref machine 10)))
                 (if direct? (apply callee args) (native-c-fallback-invoke callee args)))))
    (if tail? (native-c-return! machine value)
     (begin (vector-set! (native-c-machine-ref machine 2) destination value)
            (native-c-machine-set! machine 1 next) #f))))))
(define (native-c-drive machine)
 (let loop ()
  ;; The C function returns before any allocation, Scheme callback, park or
  ;; exception happens. No foreign continuation is captured across a C frame.
  (let* ((_ (native-c-refresh-pure-bifs! machine))
         (_ (native-c-prepare-noactor-tick! machine))
         (unit (native-c-machine-ref machine 0))
         (action ((vector-ref unit 0) machine))
         (_ (native-c-record-noactor-tick! machine))
         (_ (native-c-record-pure-bifs! machine))
         (_ (native-c-after-step!))
         (done?
          (case action
           ((1) (native-c-apply-action machine
                  (vector-ref (vector-ref unit 2) (native-c-machine-ref machine 4))
                  (native-c-slots (native-c-machine-ref machine 2) (native-c-machine-ref machine 7))))
           ((2) (native-c-apply-action machine (native-c-machine-ref machine 4) (native-c-machine-ref machine 7)))
           ((6) (native-c-apply-action machine (native-c-machine-ref machine 4)
                  ;; Every argument VALUE was rooted before this C step. The
                  ;; one fresh list also survives a callee's tail-frame clear.
                  (native-c-slots (native-c-machine-ref machine 2) (native-c-machine-ref machine 7))))
           ((3) (native-c-return! machine (native-c-machine-ref machine 4)))
           ((4)
            (vector-set! (native-c-machine-ref machine 2) (native-c-machine-ref machine 5)
             (native-c-new-closure unit (native-c-machine-ref machine 4)
              (native-c-slots (native-c-machine-ref machine 2) (native-c-machine-ref machine 7))))
            (native-c-machine-set! machine 1 (native-c-machine-ref machine 6)) #f)
           ((5)
            (native-c-machine-set! machine 1 (native-c-machine-ref machine 6))
            (parameterize ((native-logical-frames (native-c-machine-ref machine 10))) (h-tick)) #f)
           (else (error "direct C returned invalid action/pc" action)))))
   (if done? (native-c-machine-ref machine 9) (loop)))))
(define (native-c-invoke closure args)
 (let ((machine (vector (vector-ref closure 1) (vector-ref closure 2)
                 (native-c-frame closure args) '() bl-nil 0 0 '() #f bl-nil
                 (native-c-source-stack closure (native-logical-frames) #f) bl-nil
                 seed-critical (native-c-source-boundary? closure)
                 (native-c-new-extension))))
  ;; Suspension captures the machine and these bases unchanged. Only a real
  ;; raise unwinds; do not use dynamic-wind, which would also run on parking.
  (with-exception-catcher
   (lambda (exception)
    (native-c-unwind-critical! machine)
    (if (native-raised? exception) (raise exception)
     ;; Match bl-with-source-frame: attach the escaping raw host failure's
     ;; CURRENT Source frames before this child driver's parameters unwind.
     ;; Explicit class/reason/raw-trace envelopes are already complete above.
     (parameterize ((native-logical-frames (vector-ref machine 10)))
      (native-raise (native-exception-kind exception)
                    (native-exception-reason exception) (native-capture-stack)))))
   (lambda () (native-c-drive machine)))))
(set! bl-invoke (lambda (callee args)
 (let* ((plan (native-c-resolve-call callee args)) (callee (car plan)) (args (cdr plan)))
  (if (native-c-closure? callee) (native-c-invoke callee args)
   (native-c-fallback-invoke callee args)))))
(define (native-c-guard thunk)
 (bl-guard (lambda () (bl-invoke thunk '()))))
(define (native-c-try body handler after)
 (bl-try (lambda () (bl-invoke body '()))
  (lambda (kind reason trace) (bl-invoke handler (list kind reason trace)))
  (if (eq? after #f) #f (lambda () (bl-invoke after '())))))
(define (native-c-binding bindings name)
 (let ((pair (assoc name bindings)))
  (if pair (cdr pair) (error "direct C missing checked pattern binder" name))))
(define (native-c-clause-error) (error "direct C function/case clause"))
