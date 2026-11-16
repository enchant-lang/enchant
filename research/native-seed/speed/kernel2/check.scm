;; KERNEL2 native differential. Loaded after the host sources, the new
;; host/host-kernel.scm, ONE emitted rt (rt-base.scm compiled from the original
;; rt.bl, or rt-new.scm from the rewritten one) and the generated oracle.scm.
;; See speed/kernel2/check.py, which runs it in slices (interpreted gsi 4.9.5
;; segfaults in its GC after ~50k calls in one process; see speed/kernel/RESULT.md).
;;
;; Prints one line per row: "R <row> <beam-agrees 0|1> <outcome>", where the
;; outcome is written text, so check.py can compare the two sides.
;;   KERNEL2_FROM / KERNEL2_TO  row slice
;;   KERNEL2_SIDE               base | new (templates are checked on `new` only)
;;   KERNEL2_PHASE              oracle | native
(define phase (getenv "KERNEL2_PHASE" "oracle"))
(define side (getenv "KERNEL2_SIDE" "new"))
(define slice-from (string->number (getenv "KERNEL2_FROM" "0")))
(define slice-to (string->number (getenv "KERNEL2_TO" "1000000000")))
(define failures 0)
(define (fail! . parts) (set! failures (+ failures 1)) (write (cons 'FAIL parts)) (newline))
(define counts (make-table))
(define (count! label) (table-set! counts label (+ 1 (table-ref counts label 0))))

(define (same? a b)
 (cond ((eq? a b) #t)
       ((and (kernel-tagged? a 'float) (kernel-tagged? b 'float)) (eqv? (vector-ref a 1) (vector-ref b 1)))
       ((and (pair? a) (pair? b)) (and (same? (car a) (car b)) (same? (cdr a) (cdr b))))
       ((and (kernel-tagged? a 'tuple) (kernel-tagged? b 'tuple))
        (let ((x (vector-ref a 1)) (y (vector-ref b 1)))
         (and (= (vector-length x) (vector-length y))
          (let loop ((i 0)) (or (= i (vector-length x)) (and (same? (vector-ref x i) (vector-ref y i)) (loop (+ i 1))))))))
       ((and (exact-integer? a) (exact-integer? b)) (= a b))
       ((and (string? a) (string? b)) (string=? a b))
       ((or (kernel-tagged? a 'map) (kernel-tagged? a 'vec) (kernel-tagged? a 'set))
        (and (vector? b) (eq? (vector-ref a 0) (vector-ref b 0)) (bl-key-equal? a b)))
       (else #f)))
(define (exception-text e) (call-with-output-string "" (lambda (port) (display-exception e port))))
(define (run thunk) (with-exception-catcher (lambda (e) (cons 'raised e)) (lambda () (cons 'ok (thunk)))))
(define (same-outcome? x y)
 (cond ((and (eq? (car x) 'ok) (eq? (car y) 'ok)) (same? (cdr x) (cdr y)))
       ((and (eq? (car x) 'raised) (eq? (car y) 'raised))
        (let ((e (cdr x)) (f (cdr y)))
         (if (and (native-raised? e) (native-raised? f))
          (and (same? (native-exception-kind e) (native-exception-kind f))
               (same? (native-exception-reason e) (native-exception-reason f)))
          (and (not (native-raised? e)) (not (native-raised? f))
               (string=? (exception-text e) (exception-text f))))))
       (else #f)))
(define (beam-agrees? beam native)
 (cond ((eq? beam 'raised) (eq? (car native) 'raised))
       ((pair? beam) (and (eq? (car native) 'ok) (same? (cadr beam) (cdr native))))
       (else #t)))
;; Outcome text: values written; raised errors by kind/reason (native) or text.
(define (outcome-text o)
 (call-with-output-string ""
  (lambda (port)
   (if (eq? (car o) 'ok) (begin (display "ok " port) (write (cdr o) port))
    (let ((e (cdr o)))
     (display "raised " port)
     (if (native-raised? e) (write (list (native-exception-kind e) (native-exception-reason e)) port)
      (write (exception-text e) port)))))))
(define (prefix? p s) (and (>= (string-length s) (string-length p)) (string=? p (substring s 0 (string-length p)))))
(define (args-of indices) (map (lambda (i) (vector-ref oracle-corpus i)) indices))
(define (emit-row index agrees o)
 (display "R ") (display index) (display " ") (display (if agrees 1 0)) (display " ") (display (outcome-text o)) (newline))
(define guard-bifs
 '("erlang/is_list/1" "erlang/is_tuple/1" "erlang/is_float/1" "erlang/is_integer/1" "erlang/is_boolean/1"
   "erlang/is_function/1" "erlang/is_atom/1" "erlang/is_map/1" "erlang/is_binary/1" "erlang/is_bitstring/1"
   "erlang/==/2" "erlang//=/2" "erlang/=:=/2" "erlang/=/=/2" "erlang/</2" "erlang/>/2" "erlang/=</2" "erlang/>=/2"))
;; "lit/OP/SIDE/I" -> (OP SIDE I); OP itself may contain "/".
(define (last-slash s end) (let loop ((i (- end 1))) (if (char=? (string-ref s i) #\/) i (loop (- i 1)))))
(define (literal-parts key)
 (let* ((n (string-length key)) (s2 (last-slash key n)) (s1 (last-slash key s2)))
  (list (substring key 4 s1) (string->number (substring key (+ s1 1) s2)) (string->number (substring key (+ s2 1) n)))))

(define (check-row index row)
 (let* ((key (car row)) (args (args-of (cadr row))) (beam (caddr row)))
  (cond
   ((prefix? "rt/" key)
    (let* ((f (oracle-rt (substring key 3 (string-length key))))
           (o (run (lambda () (apply f args)))))
     (emit-row index (and (not (eq? beam 'unencodable)) (beam-agrees? beam o)) o)
     (count! 'rt-rows)))
   ((equal? side "base") #f)
   ((prefix? "lit/" key)
    (let* ((t (cdr (assoc key oracle-literal-templates)))
           (parts (literal-parts key))
           (leaf (native-leaf (string-append "erlang/" (car parts) "/2")))
           (lit (vector-ref oracle-corpus (caddr parts)))
           (x (car args))
           (o (run (lambda () (t x))))
           (l (run (lambda () (if (= 0 (cadr parts)) (leaf lit x) (leaf x lit))))))
     (if (same-outcome? o l) (count! 'literal-template=leaf) (fail! 'literal-template/=leaf key (cadr row) o l))
     (if (and (eq? (car o) 'ok) (boolean? (cdr o))) (count! 'literal-template-boolean) (fail! 'literal-not-boolean key))
     (if (beam-agrees? beam o) (count! 'literal-template=beam) (count! 'literal-leaf/=beam-preexisting))))
   ((and (equal? key "erlang/make_tuple/2") (exact-integer? (car args)) (not (fixnum? (car args))))
    (count! 'skipped-divergent-leaf))
   (else
    (let* ((template (assoc key oracle-templates)) (leaf (native-leaf key)))
     (if (not template) (fail! 'no-template key)
      (let ((t (run (lambda () (apply (cdr template) args)))) (l (run (lambda () (apply leaf args)))))
       (if (same-outcome? t l) (count! 'template=leaf) (fail! 'template/=leaf key (cadr row) (outcome-text t) (outcome-text l)))
       (if (member key guard-bifs)
        (if (and (eq? (car t) 'ok) (boolean? (cdr t))) (count! 'guard-bif-boolean) (fail! 'guard-bif-not-boolean key (cadr row))))
       (if (eq? beam 'unencodable) (count! 'beam-unencodable)
        (if (beam-agrees? beam t) (count! 'template=beam) (count! 'leaf/=beam-preexisting))))))))))

(if (equal? phase "oracle")
 (call-with-input-file (path-expand "oracle-cases.sexp")
  (lambda (port)
   (let loop ((index 0))
    (let ((datum (read port)))
     (if (not (eof-object? datum))
      (begin
       (if (and (>= index slice-from) (< index slice-to))
        (check-row index (list (car datum) (cadr datum)
                               (case (caddr datum) ((ok) (list 'ok (eval (cadddr datum)))) (else (caddr datum))))))
       (loop (+ index 1)))))))))

;; Native-only values (no BEAM encoding): both sides must answer alike.
(define lazy-value (native-lazy-new (lambda () bl-nil)))
(define utf16-text (native-from-utf16 '(55296)))
(define exotics
 (list (string->symbol ":nil") (string->symbol ":true") (string->symbol ":false") (string->symbol "plain")
       utf16-text (bl-key utf16-text) (native-ref-new 'atom 1) lazy-value
       (bl-struct (bl-key utf16-text) (bl-map (bl-key "a") 1)) (bl-make-tuple utf16-text 1 2)
       (bl-make-tuple (bl-key utf16-text) 1 2) (bl-make-tuple (bl-key utf16-text) 1)
       (bl-make-tuple (string->symbol ":meta") 1 (bl-map))))
(define sample (list bl-nil #t 1 (bl-key "a") "a" '() (list 1) (bl-make-tuple 1 2) (bl-map) (bl-make-vec 1) (bl-float 1.)))
(define unary '("kind-kind" "call-not-" "reduce-reduced?" "k-first" "k-rest" "k-empty?" "hash-hash-key" "to-str"
                "empty-list?" "unwrap-meta" "seq-one"))
(define binary '("k-compare" "k-eqv" "call-identical?" "k-cons" "raw-cons" "tuple2" "struct-of?" "seq-two"))
(if (equal? phase "native")
 (let ((index 0))
  (define (exotic name args)
   (let ((o (run (lambda () (apply (oracle-rt name) args)))))
    (display "X ") (display index) (display " ") (display name) (display " ") (display (outcome-text o)) (newline)
    (set! index (+ index 1))))
  (for-each (lambda (name) (for-each (lambda (x) (exotic name (list x))) exotics)) unary)
  (for-each (lambda (name)
   (for-each (lambda (x) (for-each (lambda (y) (exotic name (list x y)) (exotic name (list y x))) (append sample exotics)))
    exotics)) binary)))

(for-each (lambda (p) (display "C ") (display (car p)) (display " ") (display (cdr p)) (newline)) (table->list counts))
(if (= failures 0) (begin (display "KERNEL2_SLICE_PASS") (newline)) (exit 1))
