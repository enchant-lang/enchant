;; Native kernel: BIF template helpers (CONTRACT2 category b). Loaded AFTER
;; host-compiler.scm and host-match.scm.
;;
;; native.intrinsics/remote-template inlines the hottest Erlang BIFs at AOT link
;; time. Its expressions call the `kernel-…` procedures below; every case the
;; fixed native representation does not decide goes to the REGISTERED LEAF
;; procedure itself, captured once here (`kernel-leaf-…`), so the answer is the
;; leaf's by construction, including raised errors. Helpers never raise on
;; their own, never allocate observable identity differences and never touch
;; scheduler state.
;;
;; Nothing here re-implements priv/boot/rt.bl. The runtime's functions are
;; compiled from that source by the native compiler (workstream KERNEL).

(define (kernel-leaf key)
 (let ((value (native-leaf key)))
  (if (eq? value native-missing) (error "native kernel: missing registered leaf" key) value)))

;; Registered leaves, captured once. Fallbacks call EXACTLY these procedures.
(define kernel-leaf-is-atom (kernel-leaf "erlang/is_atom/1"))
(define kernel-leaf-is-map (kernel-leaf "erlang/is_map/1"))
(define kernel-leaf-is-binary (kernel-leaf "erlang/is_binary/1"))
(define kernel-leaf-is-bitstring (kernel-leaf "erlang/is_bitstring/1"))
(define kernel-leaf-== (kernel-leaf "erlang/==/2"))
(define kernel-leaf-=:= (kernel-leaf "erlang/=:=/2"))
(define kernel-leaf-< (kernel-leaf "erlang/</2"))
(define kernel-leaf-> (kernel-leaf "erlang/>/2"))
(define kernel-leaf-=< (kernel-leaf "erlang/=</2"))
(define kernel-leaf->= (kernel-leaf "erlang/>=/2"))
(define kernel-leaf-+ (kernel-leaf "erlang/+/2"))
(define kernel-leaf-- (kernel-leaf "erlang/-/2"))
(define kernel-leaf-* (kernel-leaf "erlang/*/2"))
(define kernel-leaf-element (kernel-leaf "erlang/element/2"))
(define kernel-leaf-tuple-size (kernel-leaf "erlang/tuple_size/1"))
(define kernel-leaf-tuple-to-list (kernel-leaf "erlang/tuple_to_list/1"))
(define kernel-leaf-setelement (kernel-leaf "erlang/setelement/3"))
(define kernel-leaf-make-tuple (kernel-leaf "erlang/make_tuple/2"))
(define kernel-leaf-list-to-tuple (kernel-leaf "erlang/list_to_tuple/1"))
(define kernel-leaf-length (kernel-leaf "erlang/length/1"))
(define kernel-leaf-hd (kernel-leaf "erlang/hd/1"))
(define kernel-leaf-tl (kernel-leaf "erlang/tl/1"))
(define kernel-leaf-not (kernel-leaf "erlang/not/1"))
(define kernel-leaf-function-exported (kernel-leaf "erlang/function_exported/3"))
(define kernel-leaf-is-function2 (kernel-leaf "erlang/is_function/2"))
(define kernel-leaf-apply3 (kernel-leaf "erlang/apply/3"))
(define kernel-leaf-integer-to-binary (kernel-leaf "erlang/integer_to_binary/1"))
(define kernel-leaf-iolist-to-binary (kernel-leaf "erlang/iolist_to_binary/1"))
(define kernel-leaf-map-get (kernel-leaf "erlang/map_get/2"))
(define kernel-leaf-map-size (kernel-leaf "erlang/map_size/1"))
(define kernel-leaf-is-map-key (kernel-leaf "erlang/is_map_key/2"))
(define kernel-leaf-append (kernel-leaf "lists/append/2"))
(define kernel-leaf-reverse (kernel-leaf "lists/reverse/1"))
(define kernel-leaf-maps-get2 (kernel-leaf "maps/get/2"))
(define kernel-leaf-maps-get3 (kernel-leaf "maps/get/3"))
(define kernel-leaf-maps-is-key (kernel-leaf "maps/is_key/2"))
(define kernel-leaf-maps-put (kernel-leaf "maps/put/3"))
(define kernel-leaf-maps-find (kernel-leaf "maps/find/2"))
(define kernel-leaf-maps-size (kernel-leaf "maps/size/1"))
(define kernel-leaf-++ (kernel-leaf "erlang/++/2"))
(define kernel-leaf-atom-to-binary2 (kernel-leaf "erlang/atom_to_binary/2"))

;; Opaque host structs are length-7 marker vectors (native-ref-new). The
;; erlang/is_map/1 template relies on "no non-vector and no 2-slot tagged vector
;; is an opaque struct"; enforce it at the single registration point instead of
;; assuming it.
(define kernel-register-struct-without-shape-check native-register-struct!)
(set! native-register-struct! (lambda (value module fields-reader)
 (if (not (and (vector? value) (> (vector-length value) 2)))
  (error "native kernel: opaque structs must be marker vectors of length > 2" value))
 (kernel-register-struct-without-shape-check value module fields-reader)))

;; ── representation tests ────────────────────────────────────────────────
(define (kernel-tagged? x tag) (and (vector? x) (eq? (vector-length x) 2) (eq? (vector-ref x 0) tag)))
;; Interned symbol whose name begins with ':' — the scalar keyword spelling.
(define (kernel-colon-symbol? x)
 (and (symbol? x)
  (let ((s (symbol->string x))) (and (fx> (string-length s) 0) (char=? (string-ref s 0) #\:)))))
;; The keyword spellings that share an atom name with bl-nil, #t and #f; the
;; equality-against-a-literal templates compare against them by identity.
(define kernel-symbol-nil (string->symbol ":nil"))
(define kernel-symbol-true (string->symbol ":true"))
(define kernel-symbol-false (string->symbol ":false"))
;; Simple value classes whose raw term equality is decided by representation.
;; 0 fixnum, 1 symbol, 2 scalar string, 3 pair, 4 (), 5 nil/boolean; #f other.
(define (kernel-simple-class x)
 (cond ((fixnum? x) 0) ((symbol? x) 1) ((string? x) 2) ((pair? x) 3) ((null? x) 4)
       ((or (boolean? x) (eq? x bl-nil)) 5) (else #f)))
;; Shared by erlang:==/2 (native-erlang-equal?) and erlang:=:=/2 (bl-key-equal?):
;; for these classes both reduce to bl-key-compare rank/name/content tests.
;; Distinct interned symbols never compare equal (colon names differ; plain
;; symbols compare by opaque identity); only symbol × nil/boolean may share
;; an atom name, and pair × pair recurses — both go to the leaf.
(define (kernel-simple-equal a b leaf)
 (if (eq? a b) #t
  (let ((ca (kernel-simple-class a)) (cb (kernel-simple-class b)))
   (cond ((or (not ca) (not cb)) (leaf a b))
         ((eq? ca cb)
          (case ca ((2) (string=? a b)) ((3) (leaf a b)) (else #f)))
         ((or (and (eq? ca 1) (eq? cb 5)) (and (eq? ca 5) (eq? cb 1))) (leaf a b))
         (else #f)))))
(define (kernel-erlang-equal? a b) (kernel-simple-equal a b kernel-leaf-==))
(define (kernel-exact-equal? a b) (kernel-simple-equal a b kernel-leaf-=:=))
(define (kernel-tuple-to-list t)
 (if (kernel-tagged? t 'tuple) (vector->list (vector-ref t 1)) (kernel-leaf-tuple-to-list t)))
(define (kernel-setelement i t v)
 (if (and (fixnum? i) (kernel-tagged? t 'tuple) (fx>= i 1) (fx<= i (vector-length (vector-ref t 1))))
  (let ((items (vector-copy (vector-ref t 1)))) (vector-set! items (fx- i 1) v) (vector 'tuple items))
  (kernel-leaf-setelement i t v)))
(define (kernel-make-tuple n x)
 (if (and (fixnum? n) (fx>= n 0))
  (let ((items (make-vector n)))
   (let fill ((i 0)) (if (fx< i n) (begin (vector-set! items i x) (fill (fx+ i 1)))))
   (vector 'tuple items))
  (kernel-leaf-make-tuple n x)))
(define (kernel-list-to-tuple xs)
 (let loop ((p xs))
  (cond ((null? p) (vector 'tuple (list->vector xs))) ((pair? p) (loop (cdr p)))
        (else (kernel-leaf-list-to-tuple xs)))))
(define (kernel-length xs)
 (let loop ((p xs) (n 0))
  (cond ((null? p) n) ((pair? p) (loop (cdr p) (fx+ n 1))) (else (kernel-leaf-length xs)))))
