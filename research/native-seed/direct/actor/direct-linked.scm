;; Captured actor-link remote bindings are private deferred control values.
;; Resolve only the exact admitted namespace/name, never a same-spelling MFA.
(define native-c-linked-marker (list 'native-c-linked-marker))
(define (native-c-linked ns name arity packed?)
 (if (not (and (string? ns) (string? name) (integer? arity) (exact? arity) (>= arity 0)
               (boolean? packed?)))
  (error "invalid captured direct actor binding" ns name arity))
 (vector native-c-linked-marker ns name arity packed?))
(define (native-c-linked? value)
 (and (vector? value) (= (vector-length value) 5)
      (eq? (vector-ref value 0) native-c-linked-marker)))
(define native-c-linked-leaf-marker (list 'native-c-linked-leaf-marker))
(define (native-c-linked-leaf key)
 ;; Source may guard an unavailable host reference with function_exported/3.
 ;; Constructing its containing C unit must not execute that reference.
 (if (not (string? key)) (error "captured actor leaf key must be text"))
 (vector native-c-linked-leaf-marker key))
(define (native-c-linked-leaf? value)
 (and (vector? value) (= (vector-length value) 2)
      (eq? (vector-ref value 0) native-c-linked-leaf-marker)))
(define native-c-resolve-without-linked native-c-resolve-call)
(set! native-c-resolve-call (lambda (callee arguments)
 (let* ((plan (native-c-resolve-without-linked callee arguments))
        (descriptor (car plan)) (args (cdr plan)))
  (cond
   ((native-c-linked-leaf? descriptor)
    (let ((key (vector-ref descriptor 1)))
     (if (member key native-excluded-host-leaves) (error "captured actor leaf is excluded" key))
     (let ((leaf (native-leaf key)))
      (if (eq? leaf native-missing) (error "captured actor leaf is absent" key))
      (native-c-resolve-without-linked leaf args))))
   ((not (native-c-linked? descriptor)) plan)
   (else (let* ((ns (vector-ref descriptor 1)) (name (vector-ref descriptor 2))
          (arity (vector-ref descriptor 3)) (packed? (vector-ref descriptor 4))
          (metadata (bl-get native-export-arities (native-row ns name) native-missing))
          (value (native-global-exact ns name)))
    (if (not (= (length args) arity)) (error "captured actor remote arity changed" ns name))
    (if (eq? metadata native-missing) (error "captured actor body lacks emitted arity" ns name))
    (if packed?
     (begin
      (if (not (and (native-multi-callable? value)
                     (not (bl-is-nil (bl-nth metadata 1)))
                     (= arity (+ 1 (bl-nth metadata 1)))
                     (not (bl-is-nil (bl-nth value 2)))))
       (error "captured actor physical variadic arm is absent" ns name))
      ;; The argument list already has the compiler's trailing rest list.
      ;; Select the raw arm once and leave its payload untouched.
      (native-c-resolve-without-linked (bl-nth (bl-nth value 2) 1) args))
     (begin
      (if (not (native-callable-accepts? value arity))
       (error "captured actor logical body arity changed" ns name))
      (if (native-c-linked? value) (error "captured actor binding resolved to itself" ns name))
      (native-c-resolve-without-linked value args)))))))))
