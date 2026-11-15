;; Optional direct-backend extension: append after direct-machine.scm. Static
;; non-host MFAs become private descriptors, never Scheme forwarding lambdas.
;; Their target resolves at INVOCATION, after exact body/arity publication.
(define native-c-remote-marker (list 'native-c-remote-marker))
(define native-c-max-explicit-depth 0)
(define native-c-max-driver-depth 0)
(define native-c-driver-depth (make-parameter 0))
(define native-c-enter-without-remote native-c-enter!)
(set! native-c-enter! (lambda (machine callee arguments destination next tail?)
 (native-c-enter-without-remote machine callee arguments destination next tail?)
 (set! native-c-max-explicit-depth
  (max native-c-max-explicit-depth (length (vector-ref machine 3))))))
(define native-c-invoke-without-remote native-c-invoke)
(set! native-c-invoke (lambda (callee arguments)
 (let ((depth (+ 1 (native-c-driver-depth))))
  (set! native-c-max-driver-depth (max native-c-max-driver-depth depth))
  (parameterize ((native-c-driver-depth depth))
   (native-c-invoke-without-remote callee arguments)))))
(define (native-c-remote? value)
 (and (vector? value) (= (vector-length value) 6)
      (eq? (vector-ref value 0) native-c-remote-marker)))
(define (native-c-parse-remote key)
 (if (not (string? key)) (error "direct C MFA key must be a string"))
 ;; A function itself can be '/', e.g. erlang///2 and core's divide export.
 ;; The first separator ends the module; only the LAST begins the arity.
 (let* ((size (string-length key))
        (separators
         (let scan ((i 0) (first #f) (last #f))
          (if (= i size) (cons first last)
           (if (char=? (string-ref key i) #\/)
            (scan (+ i 1) (or first i) i) (scan (+ i 1) first last)))))
        (first (car separators)) (last (cdr separators)))
  (if (not (and first last (> first 0) (> last (+ first 1)) (< last (- size 1))))
   (error "invalid direct C MFA key" key))
  (let* ((module (substring key 0 first))
         (function (substring key (+ first 1) last))
         (arity-text (substring key (+ last 1) size))
         (arity (string->number arity-text)))
   (if (not (and (let digits ((i 0))
                  (or (= i (string-length arity-text))
                      (and (char>=? (string-ref arity-text i) #\0)
                           (char<=? (string-ref arity-text i) #\9) (digits (+ i 1)))))
                 (integer? arity) (exact? arity) (>= arity 0)))
    (error "invalid direct C MFA arity" key))
   (let* ((n (string-length function))
          (packed? (and (>= n 6) (string=? (substring function (- n 6) n) "__bl_v")))
          (logical (if packed? (substring function 0 (- n 6)) function)))
    (if (= (string-length logical) 0) (error "empty direct C logical export" key))
    (vector native-c-remote-marker module logical arity packed? key)))))
(define (native-c-remote key)
 ;; Service tables contain inert references, including calls guarded by the
 ;; canonical Source's false function_exported probe. Reject excluded MFAs
 ;; only when native-c-remote-target resolves an ACTUAL invocation below.
 ;; host/ is the dynamically replaceable loader/IO/backend control plane.
 ;; AOT service tables must retain a live descriptor even when a host leaf is
 ;; already installed. Other existing raw BIF leaves keep their early binding.
 (if (or (member key native-excluded-host-leaves)
         (and (string? key) (>= (string-length key) 5)
              (string=? (substring key 0 5) "host/")))
  (native-c-parse-remote key)
  (let ((leaf (native-leaf key)))
   (if (eq? leaf native-missing) (native-c-parse-remote key) leaf))))
;; Cache only successful publication reads. Registry maps and the exclusion
;; list are published as persistent ROOTS; every replacement retires entries.
;; Descriptor vectors/strings are raw Scheme data, so identity alone is NOT
;; proof of unchanged content. Each hit also checks an owned six-field snapshot.
;; Cached metadata/value objects are re-read below: host mutation of a $blfn
;; clause or its arity vector must not retain an obsolete physical selection.
(define native-c-remote-target-cache (make-table test: eq? weak-keys: #t))
(define native-c-remote-target-roots (vector #f #f #f #f #f))
(define native-c-remote-target-hooks-current?
 (let ((leaf native-leaf) (row native-row) (get bl-get) (tuple bl-tuple)
       (nth bl-nth) (items bl-items) (nil? bl-is-nil)
       (multi? native-multi-callable?) (closure? native-c-closure?)
       (accepts? native-callable-accepts?) (missing native-missing))
  (lambda ()
   (and (eq? native-leaf leaf) (eq? native-row row) (eq? bl-get get)
        (eq? bl-tuple tuple) (eq? bl-nth nth) (eq? bl-items items)
        (eq? bl-is-nil nil?) (eq? native-multi-callable? multi?)
        (eq? native-c-closure? closure?) (eq? native-callable-accepts? accepts?)
        (eq? native-missing missing)))))
(define (native-c-refresh-target-cache!)
 (let ((roots native-c-remote-target-roots))
  (if (or (not (eq? (vector-ref roots 0) native-leaf-registry))
          (not (eq? (vector-ref roots 1) native-module-names))
          (not (eq? (vector-ref roots 2) native-export-arities))
          (not (eq? (vector-ref roots 3) native-global-registry))
          (not (eq? (vector-ref roots 4) native-excluded-host-leaves)))
   (begin
    (set! native-c-remote-target-cache (make-table test: eq? weak-keys: #t))
    (vector-set! roots 0 native-leaf-registry)
    (vector-set! roots 1 native-module-names)
    (vector-set! roots 2 native-export-arities)
    (vector-set! roots 3 native-global-registry)
    (vector-set! roots 4 native-excluded-host-leaves)))))
(define (native-c-target-cacheable? descriptor)
 ;; This predicate only limits the optimization. Other raw host inputs retain
 ;; the original resolver's behavior, including its exact validation/errors.
 (and (vector? descriptor) (= (vector-length descriptor) 6)
      (eq? (vector-ref descriptor 0) native-c-remote-marker)
      (string? (vector-ref descriptor 1)) (string? (vector-ref descriptor 2))
      (integer? (vector-ref descriptor 3)) (exact? (vector-ref descriptor 3))
      (>= (vector-ref descriptor 3) 0) (boolean? (vector-ref descriptor 4))
      (string? (vector-ref descriptor 5))))
(define (native-c-target-snapshot-matches? descriptor entry)
 (and (eq? (vector-ref descriptor 0) (vector-ref entry 0))
      (string=? (vector-ref descriptor 1) (vector-ref entry 1))
      (string=? (vector-ref descriptor 2) (vector-ref entry 2))
      (eqv? (vector-ref descriptor 3) (vector-ref entry 3))
      (eq? (vector-ref descriptor 4) (vector-ref entry 4))
      (string=? (vector-ref descriptor 5) (vector-ref entry 5))))
(define (native-c-remember-target! descriptor metadata value)
 (table-set! native-c-remote-target-cache descriptor
  (vector (vector-ref descriptor 0) (string-copy (vector-ref descriptor 1))
          (string-copy (vector-ref descriptor 2)) (vector-ref descriptor 3)
          (vector-ref descriptor 4) (string-copy (vector-ref descriptor 5))
          metadata value)))
;; A single fixed C body is already the physical target. Inspect its ENTIRE
;; live one-element arity storage instead of allocating bl-items and selecting
;; a dispatcher that this raw closure cannot be. Other shapes use the original
;; selector; the physical-arity operation remains live in BOTH paths.
(define native-c-single-fixed-target-hits 0)
(define native-c-single-fixed-published?
 (let ((tag? bl-tag?) (nth bl-nth) (items bl-items)
       (multi? native-multi-callable?) (closure? native-c-closure?)
       (count native-vector-count) (ref native-vector-ref)
       (storage? native-vector-storage?) (at native-vector-at))
  (lambda (arity packed? metadata value)
   (and (or native-c-noactor-tick-enabled? native-c-pure-bif-enabled?)
        (not packed?)
        (vector? value) (= (vector-length value) 7)
        (eq? (vector-ref value 0) native-c-closure-marker)
        ;; These stock operations would otherwise run before the live accepts?
        ;; call. A replacement owns its effects, including mutations/errors.
        (eq? bl-tag? tag?) (eq? bl-nth nth) (eq? bl-items items)
        (eq? native-multi-callable? multi?) (eq? native-c-closure? closure?)
        (eq? native-vector-count count) (eq? native-vector-ref ref)
        (eq? native-vector-storage? storage?) (eq? native-vector-at at)
        (vector? metadata) (= (vector-length metadata) 2)
        (eq? (vector-ref metadata 0) 'tuple)
        (let ((fields (vector-ref metadata 1)))
         (and (vector? fields) (= (vector-length fields) 2)
          (let ((fixed (vector-ref fields 0)))
           (and (vector? fixed) (= (vector-length fixed) 2)
                (eq? (vector-ref fixed 0) 'vec)
                (let ((store (vector-ref fixed 1)))
                 (and (vector? store)
                      (or (= (vector-length store) 4) (= (vector-length store) 5))
                      (eq? (vector-ref store 0) 'pvec-v1)
                      (eqv? (vector-ref store 1) 1)
                      (eqv? (vector-ref store 2) 1)
                      (eqv? (vector-ref store 3) arity)))))))))))
(define (native-c-select-published-target arity packed? key metadata value)
 (if (native-c-single-fixed-published? arity packed? metadata value)
  (begin
   ;; Never cache this result: C source[6] and its arity map remain mutable,
   ;; and native-callable-accepts? can be replaced by an effectful host hook.
   (if (not (native-callable-accepts? value arity))
    (error "direct C MFA selected an invalid physical function" key))
   (set! native-c-single-fixed-target-hits (+ native-c-single-fixed-target-hits 1))
   value)
 (let ()
  (if (not (if packed?
            (and (not (bl-is-nil (bl-nth metadata 1))) (= arity (+ 1 (bl-nth metadata 1))))
            (member arity (bl-items (bl-nth metadata 0)))))
   (error "direct C MFA violates the published export arity" key))
  (let ((target
         (if packed?
          (if (and (native-multi-callable? value) (not (bl-is-nil (bl-nth value 2))))
           (bl-nth (bl-nth value 2) 1) (error "direct C variadic physical clause is absent" key))
          (if (native-multi-callable? value)
           (let ((fixed (bl-get (bl-nth value 1) arity native-missing)))
            (if (eq? fixed native-missing) (error "direct C fixed clause is absent" key)) fixed)
           value))))
   (if (not (and (or (native-c-closure? target) (procedure? target))
                 (native-callable-accepts? target arity)))
    (error "direct C MFA selected an invalid physical function" key)) target))))
(define (native-c-remote-target-uncached descriptor remember?)
 (let* ((module (vector-ref descriptor 1)) (logical (vector-ref descriptor 2))
        (arity (vector-ref descriptor 3)) (packed? (vector-ref descriptor 4))
        (key (vector-ref descriptor 5)) (leaf (native-leaf key)))
  (if (member key native-excluded-host-leaves) (error "direct C MFA is explicitly excluded" key))
  (if (not (eq? leaf native-missing))
   (begin (if remember? (native-c-remember-target! descriptor #f leaf)) leaf)
   (let* ((namespace (bl-get native-module-names module native-missing))
          (row (and (not (eq? namespace native-missing)) (native-row namespace logical)))
          (metadata (if row (bl-get native-export-arities row native-missing) native-missing))
          (value (if row (bl-get native-global-registry (string-append namespace "/" logical) native-missing) native-missing)))
    (if (or (eq? namespace native-missing) (eq? metadata native-missing) (eq? value native-missing))
     (error "direct C MFA lacks a published source body/arity" key))
    (let ((target (native-c-select-published-target arity packed? key metadata value)))
     ;; No failure/absence can reach this publication point.
     (if remember? (native-c-remember-target! descriptor metadata value)) target)))))
(define (native-c-remote-target descriptor)
 (if (and (native-c-remote-target-hooks-current?) (native-c-target-cacheable? descriptor))
  (begin
   (native-c-refresh-target-cache!)
   (let ((entry (table-ref native-c-remote-target-cache descriptor native-missing)))
    (if (and (not (eq? entry native-missing))
             (native-c-target-snapshot-matches? descriptor entry))
     (if (vector-ref entry 6)
      (native-c-select-published-target (vector-ref descriptor 3) (vector-ref descriptor 4)
       (vector-ref descriptor 5) (vector-ref entry 6) (vector-ref entry 7))
      (vector-ref entry 7))
     (native-c-remote-target-uncached descriptor #t))))
  ;; A replacement lookup/classifier owns all its effects; do not skip it.
  (native-c-remote-target-uncached descriptor #f)))
(define native-c-resolve-without-remote native-c-resolve-call)
(set! native-c-resolve-call (lambda (callee arguments)
 (let* ((plan (native-c-resolve-without-remote callee arguments))
        (target (car plan)) (args (cdr plan)))
  (if (native-c-remote? target)
   (begin
    (if (not (= (length args) (vector-ref target 3)))
     (error "direct C static MFA argument count differs" (vector-ref target 5)))
    ;; __bl_v already receives the packed physical rest list. Select its raw
    ;; clause above; never pass it to the logical dispatcher a second time.
    (native-c-resolve-without-remote (native-c-remote-target target) args)) plan))))
(native-add-leaf! "host/native-c-control-stats/0" (lambda ()
 (bl-map (bl-key "max-driver-depth") native-c-max-driver-depth
         (bl-key "max-explicit-depth") native-c-max-explicit-depth
         (bl-key "steps") native-c-step-count)))
(native-add-leaf! "host/native-c-reset-control-stats/0" (lambda ()
 (set! native-c-max-driver-depth (native-c-driver-depth))
 (set! native-c-max-explicit-depth 0) bl-nil))
