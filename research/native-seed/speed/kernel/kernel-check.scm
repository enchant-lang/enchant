;; Native differential check for host/host-kernel.scm + native.intrinsics.
;; Loaded after the host sources, host-kernel.scm and the generated
;; out/oracle.scm (see speed/kernel/check.py).
(define check-failures '())
(define check-counts (make-table))
(define (count! label) (table-set! check-counts label (+ 1 (table-ref check-counts label 0))))
(define (fail! . parts)
 (count! 'failures)
 (if (< (length check-failures) 40) (set! check-failures (cons parts check-failures))))

;; gsi 4.9.5 (interpreted) segfaults inside its GC after ~50k leaf calls in one
;; process, with or without host-kernel.scm loaded (reproduced with a leaf-only
;; harness). check.py therefore runs the BEAM rows in slices, one process each:
;;   KERNEL_PHASE=oracle KERNEL_FROM=i KERNEL_TO=j  → sections 1–2 on rows [i, j)
;;   KERNEL_PHASE=native                            → sections 3–5
(define oracle-phase? (equal? (getenv "KERNEL_PHASE" "oracle") "oracle"))
(define native-phase? (not oracle-phase?))
(define slice-from (string->number (getenv "KERNEL_FROM" "0")))
(define slice-to (string->number (getenv "KERNEL_TO" "1000000000")))
(define row-index 0)
;; BEAM rows are data (one datum per line); only outcome values are evaluated.
(define oracle-cases
 (call-with-input-file (path-expand "oracle-cases.sexp")
  (lambda (port)
   (let loop ((rows '()))
    (let ((datum (read port)))
     (cond ((eof-object? datum) (reverse rows))
           ((or (not oracle-phase?) (< row-index slice-from) (>= row-index slice-to))
            (set! row-index (+ row-index 1)) (loop rows))
           (else
            (set! row-index (+ row-index 1))
            (loop (cons (list (car datum) (cadr datum)
                              (case (caddr datum) ((ok) (list 'ok (eval (cadddr datum)))) (else (caddr datum))))
                        rows)))))))))

;; Strict structural sameness: types, float bits, content.
(define (same? a b)
 (cond ((eq? a b) #t)
       ((and (kernel-tagged? a 'float) (kernel-tagged? b 'float)) (eqv? (vector-ref a 1) (vector-ref b 1)))
       ((and (pair? a) (pair? b)) (and (same? (car a) (car b)) (same? (cdr a) (cdr b))))
       ((and (kernel-tuple? a) (kernel-tuple? b))
        (let ((x (vector-ref a 1)) (y (vector-ref b 1)))
         (and (= (vector-length x) (vector-length y))
          (let loop ((i 0)) (or (= i (vector-length x)) (and (same? (vector-ref x i) (vector-ref y i)) (loop (+ i 1))))))))
       ((and (exact-integer? a) (exact-integer? b)) (= a b))
       ((and (string? a) (string? b)) (string=? a b))
       ((or (kernel-tagged? a 'map) (kernel-tagged? a 'vec) (kernel-tagged? a 'set))
        (and (vector? b) (eq? (vector-ref a 0) (vector-ref b 0)) (bl-key-equal? a b)))
       (else #f)))
(define (exception-text e)
 (call-with-output-string "" (lambda (port) (display-exception e port))))
(define (run thunk)
 (with-exception-catcher (lambda (e) (cons 'raised e)) (lambda () (cons 'ok (thunk)))))
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
;; BEAM outcome: (ok v) | raised | unencodable
(define (beam-agrees? beam native)
 (cond ((eq? beam 'raised) (eq? (car native) 'raised))
       ((pair? beam) (and (eq? (car native) 'ok) (same? (cadr beam) (cdr native))))
       (else #t)))
(define (args-of indices) (map (lambda (i) (vector-ref oracle-corpus i)) indices))
(define (prefix? p s) (and (>= (string-length s) (string-length p)) (string=? p (substring s 0 (string-length p)))))

(define guard-bifs
 '("erlang/is_list/1" "erlang/is_tuple/1" "erlang/is_float/1" "erlang/is_integer/1" "erlang/is_boolean/1"
   "erlang/is_function/1" "erlang/is_atom/1" "erlang/is_map/1" "erlang/is_binary/1" "erlang/is_bitstring/1"
   "erlang/==/2" "erlang//=/2" "erlang/=:=/2" "erlang/=/=/2" "erlang/</2" "erlang/>/2" "erlang/=</2" "erlang/>=/2"))
;; ── 1. templates: identical to the registered leaf; leaf/BEAM agreement noted
(define leaf-beam-differences (make-table))
(for-each (lambda (row)
 (let* ((key (car row)) (args (args-of (cadr row))) (beam (caddr row))
        (template (assoc key oracle-templates)))
  (if (not (prefix? "rt/" key))
   (if (and (equal? key "erlang/make_tuple/2") (exact-integer? (car args)) (not (fixnum? (car args))))
    ;; the leaf (native-repeat) would build a 2^70-element list; BEAM: system_limit
    (count! 'skipped-divergent-leaf)
   (if (not template) (fail! 'no-template key)
    (let ((leaf (native-leaf key)))
     (let ((t (run (lambda () (apply (cdr template) args)))) (l (run (lambda () (apply leaf args)))))
      (if (same-outcome? t l) (count! 'template=leaf) (fail! 'template/=leaf key (cadr row) t l))
      ;; Guard-position BIFs (C emits a plain `if`): never raise, exactly #t/#f.
      (if (member key guard-bifs)
       (if (and (eq? (car t) 'ok) (boolean? (cdr t))) (count! 'guard-bif-boolean) (fail! 'guard-bif-not-boolean key (cadr row) t)))
      (if (eq? beam 'unencodable) (count! 'beam-unencodable)
       (if (beam-agrees? beam t) (count! 'template=beam)
        (begin (count! 'leaf/=beam-preexisting)
         (if (getenv "KERNEL_SHOW_LEAF_DIFF" #f) (begin (write (list 'leaf/=beam key (cadr row) beam t)) (newline)))
         (table-set! leaf-beam-differences key (+ 1 (table-ref leaf-beam-differences key 0)))))))))))))
 oracle-cases)

;; ── 2. overrides: fast answers equal BEAM; misses delegate to `original`
(define (override name) (let ((hit (assoc name oracle-overrides))) (and hit (cdr hit))))
(define (call-override name args)
 (set! oracle-delegated #f)
 (let ((outcome (run (lambda () (apply (override name) args)))))
  (if oracle-delegated 'delegated outcome)))
(for-each (lambda (row)
 (let ((key (car row)))
  (if (prefix? "rt/" key)
   (let* ((name (substring key 3 (string-length key))) (args (args-of (cadr row))) (beam (caddr row)))
    (if (not (override name)) (fail! 'no-override name)
     (let ((r (call-override name args)))
      (cond ((eq? r 'delegated) (count! 'override-delegated))
            ((eq? (car r) 'raised) (fail! 'fast-path-raised name (cadr row) (exception-text (cdr r))))
            ((eq? beam 'unencodable) (count! 'override-fast-unencodable))
            ((beam-agrees? beam r) (count! 'override-fast=beam))
            ;; The body IS one registered leaf call: its native answer is the
            ;; leaf's, whatever BEAM says (a leaf/BEAM difference, not ours).
            ((and (member name '("call-identical?" "identical?"))
                  (same-outcome? r (run (lambda () (apply (native-leaf "erlang/=:=/2") args)))))
             (count! 'override=leaf/=beam-preexisting))
            (else (fail! 'override/=beam name (cadr row) beam (cdr r))))))))))
 oracle-cases)

;; ── 3. native-only values: decided answers by hand, everything else delegates
(define lazy-value (native-lazy-new (lambda () bl-nil)))
(define utf16-text (native-from-utf16 '(55296)))
(define exotics
 (list (string->symbol ":nil") (string->symbol ":true") (string->symbol ":false") (string->symbol "plain")
       utf16-text (bl-key utf16-text) (native-ref-new 'atom 1) (lambda (x) x) lazy-value
       (bl-struct (bl-key utf16-text) (bl-map (bl-key "a") 1)) (bl-make-tuple utf16-text 1 2)
       (bl-make-tuple (bl-key utf16-text) 1 2) (bl-make-tuple (bl-key utf16-text) 1)))
(define sample (list bl-nil #t 1 (bl-key "a") "a" '() (list 1) (bl-make-tuple 1 2) (bl-map) (bl-make-vec 1) (bl-float 1.)))
(define (expected name args)
 ;; 'delegated, or (ok value) derived by hand from rt.bl over the registered leaves
 (let ((x (car args)))
  (cond ((and (member name '("k-eqv" "eqv")) (= (length args) 2) (eq? x (cadr args))) (list 'ok #t))
        ((and (member name '("k-compare" "compare")) (= (length args) 2) (eq? x (cadr args))) (list 'ok 0))
        ;; hash-hash-key: a symbol is neither tuple, map nor list
        ((and (member name '("hash-hash-key" "hash_key")) (symbol? x)) (list 'ok x))
        ((and (member name '("hash-hash-key" "hash_key")) (kernel-tuple? x) (not (= 3 (bl-count x)))) (list 'ok x))
        ;; (and (erlang/is_map x) (… (maps/get :__struct__ x nil) …)) over the leaves
        ((member name '("struct-of?" "reduce-reduced?"))
         (cond ((or (kernel-tagged? x 'map) (kernel-tagged? x 'vec) (kernel-tagged? x 'set))
                (let ((mod ((native-leaf "maps/get/3") (bl-key "__struct__") x bl-nil)))
                 (list 'ok (if (equal? name "struct-of?") ((native-leaf "erlang/=:=/2") (cadr args) mod)
                            ((native-leaf "erlang/==/2") mod (bl-key "Elixir.BeamLisp.Reduced"))))))
               ((or (symbol? x) (fixnum? x) (string? x) (boolean? x) (eq? x bl-nil) (pair? x) (null? x)
                    (kernel-tuple? x) (kernel-tagged? x 'float)) (list 'ok #f))
               (else 'delegated)))
        ;; kind-kind: :true/:false/plain-colon symbols are atoms; the LazySeq
        ;; struct module is literally registered
        ((and (equal? name "kind-kind") (or (eq? x (string->symbol ":true")) (eq? x (string->symbol ":false"))))
         (list 'ok (bl-key "atom")))
        ((and (equal? name "kind-kind") (eq? x lazy-value)) (list 'ok (bl-key "lazy")))
        ((and (equal? name "to-str") (or (eq? x (string->symbol ":true")) (eq? x (string->symbol ":false"))))
         (list 'ok (native-atom-name x)))
        ((and (member name '("k-cons" "cons")) (let ((xs (cadr args))) (or (null? xs) (pair? xs) (eq? xs bl-nil))))
         (list 'ok (cons x (if (eq? (cadr args) bl-nil) '() (cadr args)))))
        ((and (member name '("k-cons" "cons")) (kernel-tagged? (cadr args) 'vec)) (list 'ok (cons x (bl-items (cadr args)))))
        (else 'delegated))))
(define partial-names
 '("kind-kind" "call-not-" "not_" "reduce-reduced?" "k-first" "first" "k-rest" "rest" "k-empty?" "empty?"
   "hash-hash-key" "hash_key" "to-str" "k-compare" "compare" "k-eqv" "eqv" "k-cons" "cons" "struct-of?"))
(define (override-arity name) (if (member name '("k-compare" "compare" "k-eqv" "eqv" "k-cons" "cons" "struct-of?")) 2 1))
(define (exotic-check name args)
 (let ((r (call-override name args)) (e (expected name args)))
  (cond ((and (eq? e 'delegated) (eq? r 'delegated)) (count! 'exotic-delegated))
        ((and (pair? e) (pair? r) (eq? (car r) 'ok) (same? (cadr e) (cdr r))) (count! 'exotic-decided))
        (else (fail! 'exotic name args e r)))))
(if native-phase? (for-each (lambda (name)
 (for-each (lambda (x)
  (if (= (override-arity name) 1) (exotic-check name (list x))
   (for-each (lambda (y) (exotic-check name (list x y)) (exotic-check name (list y x))) (append sample exotics))))
  exotics))
 partial-names))

;; ── 4. total constructors and private bodies without a BEAM export
(define (check-total name args value)
 (let ((r (call-override name args)))
  (if (and (pair? r) (eq? (car r) 'ok) (same? (cdr r) value)) (count! 'total-native) (fail! 'total name args r))))
(if native-phase? (for-each (lambda (x)
 (check-total "seq-one" (list x) (list x)) (check-total "reduce-one" (list x) (list x))
 (for-each (lambda (y) (check-total "seq-two" (list x y) (list x y)) (check-total "reduce-two" (list x y) (list x y))
                       (check-total "raw-cons" (list x y) (cons x y)))
  (append sample exotics)))
 (append sample exotics)))
(if native-phase? (let ((f (lambda (x) x)))
 ;; No Env gate exports: identity, decided after the entry tick.
 (check-total "source-callable!" (list f) f)
 (check-total "source-invocation!" (list f '()) f)
 (check-total "source-invocation1!" (list f 1) f)
 (check-total "source-invocation2!" (list f 1 2) f)
 ;; Expose the gate leaves (as a managed preparation would): every gate delegates.
 (set! native-excluded-host-leaves '())
 (if (eq? native-missing (native-leaf "Elixir.BeamLisp.Env/check_source_callable!/1"))
  (native-add-leaf! "Elixir.BeamLisp.Env/check_source_callable!/1" (lambda (f) bl-nil)))
 (for-each (lambda (name args)
  (if (eq? (call-override name args) 'delegated) (count! 'gate-delegated) (fail! 'gate name)))
  '("source-callable!" "source-invocation!" "source-invocation1!" "source-invocation2!")
  (list (list f) (list f '()) (list f 1) (list f 1 2)))))

;; ── 5. call protocol: arity annotation, wrong-arity delegation, tick budget
(if native-phase? (for-each (lambda (row)
 (let ((name (car row)) (f (cdr row)))
  (if (not (procedure? f)) (fail! 'not-procedure name))
  (set! oracle-delegated #f)
  (f 1 2 3 4 5 6 7)
  (if oracle-delegated (count! 'wrong-arity-delegated) (fail! 'wrong-arity name))))
 oracle-overrides))
(define (ticks thunk)
 (set! seed-frame (vector #f)) (set! seed-budget 1000000)
 (thunk)
 (let ((spent (- 1000000 seed-budget))) (set! seed-frame #f) spent))
(define (tick-check label expected thunk)
 (if (= expected (ticks thunk)) (count! 'tick-ok) (fail! 'tick label)))
(if native-phase? (begin
(tick-check "fast" 1 (lambda () ((override "k-eqv") 1 2)))
(tick-check "miss" 0 (lambda () ((override "k-eqv") (bl-make-vec 1) (list 1))))
(tick-check "total" 1 (lambda () ((override "raw-cons") 1 '())))
(tick-check "gate" 1 (lambda () ((override "source-callable!") car)))
(if (with-exception-catcher (lambda (e) #t) (lambda () (native-register-struct! (list 1) (bl-key "X") (lambda (x) x)) #f))
 (count! 'opaque-guard) (fail! 'opaque-guard))))

(define (report label) (display label) (display " ") (display (table-ref check-counts label 0)) (newline))
(for-each report '(guard-bif-boolean override=leaf/=beam-preexisting skipped-divergent-leaf template=leaf template=beam leaf/=beam-preexisting beam-unencodable
                   override-fast=beam override-delegated override-fast-unencodable
                   exotic-decided exotic-delegated total-native gate-delegated wrong-arity-delegated tick-ok opaque-guard failures))
(for-each (lambda (p) (display "leaf/=beam ") (display (car p)) (display " ") (display (cdr p)) (newline)) (table->list leaf-beam-differences))
(for-each (lambda (f) (write f) (newline)) (reverse check-failures))
(if (= 0 (table-ref check-counts 'failures 0)) (begin (display "KERNEL_DIFFERENTIAL_PASS") (newline)) (exit 1))
