;; Direct pattern decisions emitted by native.scheme (src/native/scheme.bl).
;; Each helper is the exact step host bl-match (host-values.scm) performs:
;; map entries distinguish a missing key from a nil value, struct patterns
;; compare the module with bl-key-equal? and read fields from
;; native-struct-fields, and a vector's items match as a tuple. Load after
;; host-values.scm (it only references host procedures at call time).
(define (bl-match-entry m key)
 (let ((entry (native-map-entry m key))) (if (eq? entry native-missing) #f entry)))
(define bl-match-struct-key (bl-key "__struct__"))
(define (bl-match-struct-fields v mod)
 ;; A plain map is its own field map; skip building one in that common case.
 (if (bl-tag? v 'map)
  (and (bl-key-equal? (bl-get v bl-match-struct-key) mod) v)
  (let ((fields (native-struct-fields v)))
   (and (bl-tag? fields 'map) (bl-key-equal? (native-struct-module v) mod) fields))))
(define (bl-match-vector-count v) (native-vector-count v))
(define (bl-match-vector-ref v i) (native-vector-ref v i))
(define (bl-match-vector-items v) (bl-tuple (bl-items v)))
