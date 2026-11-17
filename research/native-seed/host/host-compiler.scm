;; Closed native compiler registry. Append after host-values.scm and raw leaves.
;; Source/BEAM custody is deliberately absent; missing host calls raise with
;; their exact module/function/arity instead of consulting a guessed alias.
(define native-env-rows (bl-empty-map))
(define native-module-names (bl-empty-map))
(define native-namespace-modules (bl-empty-map))
(define native-export-arities (bl-empty-map))
(define native-stub-names (bl-empty-map))
(define native-env-current "user")
(define native-bundle-metadata bl-nil)
(define (native-row . parts) (bl-tuple parts))
(define (native-env-value key)
 (bl-get native-env-rows key native-missing))
;; Explicit debugging only: never print a macro value, body or source text.
;; Gambit's public current-time/time->seconds supplies wall-clock seconds;
;; this does not change the actor runtime's separately selected clock.
(define native-macro-trace-enabled? (equal? (getenv "BL_NATIVE_TRACE" #f) "1"))
(define native-macro-trace-start
 (if native-macro-trace-enabled? (time->seconds (current-time)) #f))
(define (native-env-put! key value)
 (set! native-env-rows (bl-assoc native-env-rows key value))
 (native-env-row-changed! key)
 (if (and native-macro-trace-enabled?
          (bl-tag? value 'tuple) (= (bl-count value) 2)
          (eq? (bl-nth value 0) (bl-key "$macro"))
          (bl-tag? key 'tuple) (= (bl-count key) 2)
          (string? (bl-nth key 0)) (string? (bl-nth key 1)))
  (let ((now (time->seconds (current-time))) (port (current-error-port)))
   (display "NATIVE_MACRO_STORED " port)
   (write now port) (display " " port)
   (write (- now native-macro-trace-start) port) (display " " port)
   (write (bl-nth key 0) port) (display " " port)
   (write (bl-nth key 1) port) (newline port) (force-output port)))
 (bl-key "ok"))

(define (native-env-result value)
 (if (eq? value native-missing) (bl-key "error") (bl-tuple (list (bl-key "ok") value))))
(define (native-lookup key) (native-env-result (native-env-value key)))
(define (native-string-split-once text separator)
 (let loop ((i 0))
  (cond ((>= i (string-length text)) #f)
        ((char=? (string-ref text i) separator)
         (cons (substring text 0 i) (substring text (+ i 1) (string-length text))))
        (else (loop (+ i 1))))))
(define (native-candidates ns name)
 (let ((split (native-string-split-once name #\/)))
  (if (and split (> (string-length (car split)) 0) (> (string-length (cdr split)) 0))
   (let ((alias (native-env-value (native-row (bl-key "alias") ns (car split)))))
    (list (cons (if (eq? alias native-missing) (car split) alias) (cdr split))))
   (let ((refer (native-env-value (native-row (bl-key "refer") ns name))))
    (append (list (cons ns name))
     (if (eq? refer native-missing) '() (list (cons refer name)))
     (list (cons "core" name) (cons "sugar" name)))))))
(define (native-exact-candidates ns name)
 (let loop ((ns ns) (seen '()))
  (if (or (eq? ns native-missing) (member ns seen)) '()
   (cons (cons ns name)
    (loop (native-env-value (native-row (bl-key "refer") ns name)) (cons ns seen))))))
(define (native-resolve-row candidates kind compiled?)
 (if (null? candidates) native-missing
  (let* ((item (car candidates)) (ns (car item)) (name (cdr item))
         (key (if kind (native-row kind ns name) (native-row ns name)))
         (value (native-env-value key))
         (value (if (and (eq? value native-missing) compiled?)
                 (bl-get native-global-registry (string-append ns "/" name) native-missing) value)))
   (if (eq? value native-missing) (native-resolve-row (cdr candidates) kind compiled?)
    (cons ns value)))))
;; A successful global selection is valid only under BOTH immutable registry
;; roots. Any intern/redefinition/refer/alias/shadowing change retires it before
;; the next lookup. Missing bindings are never cached. Macro tuple unwrapping
;; remains in native-global/native-global-exact AFTER this raw-value selection.
(define native-global-cache (make-table test: equal?))
(define native-global-cache-env #f)
(define native-global-cache-compiled #f)
(define (native-refresh-global-cache!)
 (if (or (not (eq? native-global-cache-env native-env-rows))
         (not (eq? native-global-cache-compiled native-global-registry)))
  (begin
   (set! native-global-cache (make-table test: equal?))
   (set! native-global-cache-env native-env-rows)
   (set! native-global-cache-compiled native-global-registry))))
;; Internal consumers need the selected VALUE; the public Env.fetch adapter
;; alone needs its {:ok,value}/:error transport tag. Share the same exact
;; selection and root epochs without constructing a tuple to discard it.
(define (native-fetch-value ns name exact?)
 (native-refresh-global-cache!)
 (let* ((key (vector ns name exact?))
        (cached (table-ref native-global-cache key native-missing)))
  (if (not (eq? cached native-missing)) cached
   (let ((row (native-resolve-row
               (if exact? (native-exact-candidates ns name) (native-candidates ns name)) #f #t)))
    (if (eq? row native-missing) native-missing
     (let ((value (cdr row)))
      (table-set! native-global-cache key value)
      value))))))
(define (native-fetch ns name . exact)
 (native-env-result (native-fetch-value ns name (if (and (pair? exact) (car exact)) #t #f))))
(define (native-fetch! ns name . exact)
 (let ((value (native-fetch-value ns name (if (and (pair? exact) (car exact)) #t #f))))
  (if (eq? value native-missing) (error "undefined native var" ns name) value)))

(define (native-global ns name)
 (let ((value (native-fetch! ns name)))
  (if (and (bl-tag? value 'tuple) (= (bl-count value) 2) (eq? (bl-nth value 0) (bl-key "$macro")))
   (bl-nth value 1) value)))
(define (native-global-exact ns name)
 (let ((value (native-fetch! ns name #t)))
  (if (and (bl-tag? value 'tuple) (= (bl-count value) 2) (eq? (bl-nth value 0) (bl-key "$macro")))
   (bl-nth value 1) value)))
;; Resolve the live EXACT canonical runtime when Enum consumes a deferred
;; collection. SeqCursor has a canonical source fold, but no k-to-list kind.
;; This callback is only a raw storage primitive; BL owns cursor traversal.
(define native-cursor-list-step
 (bl-register-callable!
  (native-mark-host-callable! (lambda (acc element) (cons element acc))) 2))
(set! native-canonical-sequence-items
 (lambda (value)
  (if (native-cursor? value)
   (reverse (bl-invoke (native-global-exact "rt" "lazy-fold-source")
             (list native-cursor-list-step '() value)))
   (bl-invoke (native-global-exact "rt" "k-to-list") (list value)))))
(define (native-local-var? ns name)
 ;; A present nil/false value is a binding too. Compiled definitions and live
 ;; interns share local_var?'s Source-visible value domain.
 (or (native-map-has? native-env-rows (native-row ns name))
     (native-map-has? native-global-registry (string-append ns "/" name))))
(define (native-env-link ns name owner?)
 (if owner?
  ;; Canonical Env.link_owner stops at a local VALUE without link metadata:
  ;; baking a later core link would change the Source call's identity.
  (let loop ((candidates (native-candidates ns name)))
   (if (null? candidates) (bl-key "error")
    (let* ((candidate (car candidates)) (owner (car candidate)) (member (cdr candidate))
           (info (native-env-value (native-row (bl-key "link") owner member))))
     (cond ((not (eq? info native-missing)) (bl-tuple (list (bl-key "ok") owner info)))
           ((native-local-var? owner member) (bl-key "error"))
           (else (loop (cdr candidates)))))))
  ;; Plain Env.link deliberately keeps its canonical links-only fallback.
  (let ((row (native-resolve-row (native-candidates ns name) (bl-key "link") #f)))
   (if (eq? row native-missing) (bl-key "error")
    (bl-tuple (list (bl-key "ok") (cdr row)))))))
(define (native-intern ns name value)
 (native-env-put! (native-row ns name) value) value)
(define (native-declare-ns ns) (native-env-put! (native-row (bl-key "ns") ns) #t))
(define (native-in-ns ns) (set! native-env-current ns) (native-declare-ns ns))
(define (native-meta ns name)
 (let ((v (native-env-value (native-row (bl-key "meta") ns name))))
  (native-env-result v)))
(define (native-put-meta ns name value)
 (let* ((key (native-row (bl-key "meta") ns name))
        (previous (bl-get native-env-rows key (bl-empty-map))))
  (native-env-put! key
   (let loop ((pairs (native-map-pairs value)) (m previous))
    (if (null? pairs) m
     (loop (cdr pairs) (bl-assoc m (bl-nth (car pairs) 0) (bl-nth (car pairs) 1))))))))
(define (native-module-name module)
 (if (native-keyword? module) (native-atom-name module) module))
(define (native-register-arities! ns name fixed variadic)
 (set! native-export-arities
  (bl-assoc native-export-arities (native-row ns name) (bl-tuple (list fixed variadic))))
 (set! native-availability-cache (make-table test: equal?))
 (bl-key "ok"))
(define native-excluded-host-leaves
 '("Elixir.BeamLisp.Env/check_source_callable!/1"
   "Elixir.BeamLisp.Env/check_source_invocation!/2"
   "Elixir.BeamLisp.Env/check_source_invocation1!/2"
   "Elixir.BeamLisp.Env/check_source_invocation2!/3"
   "Elixir.BeamLisp.Env/assert_native_framework_execution!/0"))
;; Dynamic link state changes only through explicit publication points:
;; native-add-leaf!/native-replace-leaf!, native-install-bundle! and
;; native-register-arities!. Each one retires the memo tables below.
(define native-availability-cache (make-table test: equal?))
(define native-remote-table (make-table test: equal?))
(set! native-link-changed!
 (lambda ()
  (set! native-availability-cache (make-table test: equal?))
  (set! native-remote-table (make-table test: equal?))))
(define (native-remote-available-uncached? module function arity)
 (let* ((module (native-module-name module)) (function (native-module-name function))
        (key (string-append module "/" function "/" (number->string arity)))
        (ns (bl-get native-module-names module native-missing)))
  (and (not (member key native-excluded-host-leaves))
   (or (native-map-has? native-leaf-registry key)
    (and (not (eq? ns native-missing))
     (let* ((size (string-length function))
            (variadic? (and (>= size 6) (string=? (substring function (- size 6) size) "__bl_v")))
            (name (if variadic? (substring function 0 (- size 6)) function))
            (info (bl-get native-export-arities (native-row ns name) native-missing)))
      (and (not (eq? info native-missing))
       (if variadic?
        (and (not (bl-is-nil (bl-nth info 1))) (= arity (+ 1 (bl-nth info 1))))
        (if (member arity (bl-items (bl-nth info 0))) #t #f)))))))))
;; Source function_exported/3 passes immutable atoms: memoize those exact
;; booleans. Mutable strings and exceptions never enter the memo.
(define (native-remote-available? module function arity)
 (if (and (symbol? module) (symbol? function) (integer? arity) (exact? arity))
  (let* ((key (vector module function arity))
         (cached (table-ref native-availability-cache key native-missing)))
   (if (not (eq? cached native-missing)) cached
    (let ((available (native-remote-available-uncached? module function arity)))
     (if (boolean? available) (table-set! native-availability-cache key available))
     available)))
  (native-remote-available-uncached? module function arity)))
(define (native-remote-key-parts key)
 ;; Function names can contain '/', e.g. core// or erlang//=. The FIRST
 ;; separator ends the module; only the LAST separator begins the arity.
 (and (string? key)
  (let ((size (string-length key)))
   (let first ((i 0))
    (cond ((>= i size) #f)
     ((char=? (string-ref key i) #\/)
      (and (> i 0)
       (let last ((j (- size 1)))
        (cond ((<= j (+ i 1)) #f)
         ((char=? (string-ref key j) #\/)
          (and (< j (- size 1))
           (let digits ((k (+ j 1)))
            (if (= k size)
             (let* ((text (substring key (+ j 1) size)) (arity (string->number text)))
              (and (integer? arity) (exact? arity) (>= arity 0)
                   (string=? text (number->string arity))
                   (vector (substring key 0 i) (substring key (+ i 1) j) arity)))
             (let ((c (string-ref key k)))
              (and (char>=? c #\0) (char<=? c #\9) (digits (+ k 1))))))))
         (else (last (- j 1)))))))
     (else (first (+ i 1))))))))

;; ---- AOT link cells ------------------------------------------------------
;; AOT-emitted code (native.chunks) calls Scheme top-level cells directly:
;;   v_<slot>      compiled value      v_<slot>$<n>  fixed arity-n entry
;;   v_<slot>$v    variadic arm        v_<slot>$g    global view, macro-unwrapped
;;   lv_<key>      host leaf (native-add-leaf!)
;; Each linked definition registers its setters here; every later publication
;; of that slot (native-register!, an env row put/delete) runs them, so a
;; redefinition is observed exactly as the former live lookup observed it.
(define (native-unmacro value)
 (if (and (bl-tag? value 'tuple) (= (bl-count value) 2) (eq? (bl-nth value 0) (bl-key "$macro")))
  (bl-nth value 1) value))
(define (native-arity-entry value arity)
 (cond ((procedure? value) value)
  ((native-multi-callable? value)
   (let ((fixed (bl-get (bl-nth value 1) arity native-missing)))
    (if (procedure? fixed) fixed (lambda arguments (bl-invoke value arguments)))))
  (else (lambda arguments (bl-invoke value arguments)))))
(define (native-variadic-entry value key)
 (if (and (native-multi-callable? value) (not (bl-is-nil (bl-nth value 2))))
  (let ((arm (bl-nth (bl-nth value 2) 1)))
   (if (procedure? arm) arm (lambda arguments (bl-invoke arm arguments))))
  (lambda arguments (error "native variadic clause missing" key))))
(define (native-unlinked ns name)
 (lambda arguments (error "undefined native var" ns name)))
;; The global view of ns/name: its env row when present, else the compiled value.
(define (native-global-view ns name record)
 (let ((row (native-env-value (native-row ns name))))
  (if (eq? row native-missing) (vector-ref record 0) row)))
(set! native-publish-global!
 (lambda (ns name record)
  (let ((setter (vector-ref record 2)))
   (if setter
    (let ((value (native-global-view ns name record)))
     (if (not (eq? value native-missing)) (setter (native-unmacro value))))))))
(define (native-link! ns name slot-setter global-setter)
 (let ((record (native-link-record (string-append ns "/" name))))
  (vector-set! record 1 slot-setter)
  (vector-set! record 2 global-setter)
  (if (not (eq? (vector-ref record 0) native-missing)) (slot-setter (vector-ref record 0)))
  (native-publish-global! ns name record)
  (bl-key "ok")))
(define (native-link-global! ns name global-setter)
 (let ((record (native-link-record (string-append ns "/" name))))
  (vector-set! record 2 global-setter)
  (native-publish-global! ns name record)
  (bl-key "ok")))
(define (native-env-row-changed! key)
 (if (and (bl-tag? key 'tuple) (= (bl-count key) 2) (string? (bl-nth key 0)) (string? (bl-nth key 1)))
  (let ((record (table-ref native-link-records (string-append (bl-nth key 0) "/" (bl-nth key 1)) #f)))
   (if record (native-publish-global! (bl-nth key 0) (bl-nth key 1) record)))))

;; ---- Dynamic MFA lookup ----------------------------------------------------
;; Only runtime-evaluated code (native.eval/context, bootstrap --compile
;; output), erlang/apply/3, make_fun/3 and explicit host calls reach this.
;; A compiled target reads its link record's value on every call.
(define (native-remote-resolve key)
 (let ((parts (native-remote-key-parts key)))
  (if (not parts) (error "invalid native remote key" key)
   (let ((leaf (bl-get native-leaf-registry key native-missing)))
    (if (not (eq? leaf native-missing))
     (begin (table-set! native-remote-table (string-copy key) leaf) leaf)
     (let* ((module (vector-ref parts 0)) (name (vector-ref parts 1))
            (ns (bl-get native-module-names module native-missing))
            (stub (bl-get native-stub-names module native-missing))
            (size (string-length name))
            (variadic? (and (>= size 6) (string=? (substring name (- size 6) size) "__bl_v")))
            (logical (if variadic? (substring name 0 (- size 6)) name)))
      (cond
       ((not (eq? ns native-missing))
        (let* ((record (native-link-record (string-append ns "/" logical)))
               (wrapper
                (lambda arguments
                 (let ((value (vector-ref record 0)))
                  (cond ((eq? value native-missing) (error "missing compiled native export" key))
                   (variadic?
                    (if (and (native-multi-callable? value) (not (bl-is-nil (bl-nth value 2))))
                     (bl-invoke (bl-nth (bl-nth value 2) 1) arguments)
                     (error "native variadic clause missing" key)))
                   (else (bl-invoke value arguments)))))))
         (table-set! native-remote-table (string-copy key) wrapper)
         wrapper))
       ((not (eq? stub native-missing))
        (lambda arguments (error "native target explicitly excludes namespace" stub key)))
       (else (error "unimplemented native host leaf" key)))))))))
(define (native-remote key)
 (let ((hit (table-ref native-remote-table key #f)))
  (or hit (native-remote-resolve key))))

;; Named arithmetic for native.eval's :arithmetic-resolver (no per-operation closure).
(define (native-arith-add a b) (native-num 'add a b))
(define (native-arith-sub a b) (native-num 'sub a b))
(define (native-arith-mul a b) (native-num 'mul a b))
(define (native-arith-div a b) (native-num 'div a b))
(define (native-arith-lt a b) (native-num 'lt a b))
(define (native-arith-gt a b) (native-num 'gt a b))
(define (native-arith-le a b) (native-num 'le a b))
(define (native-arith-ge a b) (native-num 'ge a b))
(define (native-arith-num-eq a b) (native-num 'num_eq a b))

(define (native-install-bundle! metadata)
 (set! native-bundle-metadata metadata)
 (for-each
  (lambda (row)
   (let ((ns (bl-nth row 0)))
    (native-declare-ns ns)
    (set! native-namespace-modules (bl-assoc native-namespace-modules ns (bl-nth row 1)))
    (for-each (lambda (module)
      (set! native-module-names (bl-assoc native-module-names (native-module-name module) ns)))
     (list (bl-nth row 1) (bl-nth row 2)))))
  (bl-items (bl-get metadata (bl-key "namespace-modules"))))
 ; CompilerData's exact host implementation is already written in BL.
 (set! native-module-names (bl-assoc native-module-names "Elixir.BeamLisp.CompilerData" "host.compiler-data"))
 (set! native-module-names (bl-assoc native-module-names "Elixir.BeamLisp.FormMeta" "host.form-meta"))
 (set! native-module-names (bl-assoc native-module-names "Elixir.BeamLisp.Meta" "host.meta"))
 (for-each (lambda (row)
   (for-each (lambda (module)
     (set! native-stub-names (bl-assoc native-stub-names (native-module-name module) (bl-nth row 0))))
    (list (bl-nth row 1) (bl-nth row 2))))
  (bl-items (bl-get metadata (bl-key "stub-modules") (bl-vec '()))))
 (for-each (lambda (row)
   (native-env-put! (native-row (bl-key "link") "core" (bl-nth row 0)) (bl-nth row 1)))
  (bl-items (bl-get metadata (bl-key "core-links"))))
 (native-install-resolution! (bl-get metadata (bl-key "resolution")))
 (native-link-changed!)
 (bl-key "ok"))
(define (native-install-resolution! ledger)
 (if (not (bl-is-nil ledger))
  (begin
   (if (not (= 1 (bl-get ledger (bl-key "version")))) (error "unsupported native namespace ledger"))
   (for-each (lambda (entry) (native-declare-ns (bl-nth entry 0)))
    (native-map-pairs (bl-get ledger (bl-key "seed-names"))))
   (for-each
    (lambda (entry)
     (let* ((ns (bl-nth entry 0)) (header (bl-nth entry 1)))
      (for-each (lambda (pair)
       (native-env-put! (native-row (bl-key "alias") ns (bl-nth pair 0)) (bl-nth pair 1)))
       (native-map-pairs (bl-get header (bl-key "aliases"))))
      (for-each (lambda (pair)
       (native-env-put! (native-row (bl-key "refer") ns (bl-nth pair 0)) (bl-nth pair 1)))
       (native-map-pairs (bl-get header (bl-key "refers"))))
      (native-env-put! (native-row (bl-key "refer_clojure_exclude") ns)
       (bl-items (bl-get header (bl-key "core-excludes"))))))
    (native-map-pairs (bl-get ledger (bl-key "headers")))))))
(define (native-known-ns? ns)
 (not (eq? native-missing (native-env-value (native-row (bl-key "ns") ns)))))
(define (native-ensure-loaded ns)
 (if (or (native-known-ns? ns) (member ns (bl-items (bl-get native-bundle-metadata (bl-key "stubs") (bl-vec '())))))
  (bl-key "ok") (error "namespace absent from native compiler closure" ns)))
(define (native-main arguments)
 ; The executable dispatch itself is compiled BL, including its source reader
 ; and all compiler/emitter algorithms. No call to bl/BEAM appears here.
 (bl-invoke (native-global "native.bootstrap" "main") (list arguments)))

(define (native-env-leaf! name arity procedure)
 (native-add-leaf! (string-append "Elixir.BeamLisp.Env/" name "/" (number->string arity)) procedure))
(native-env-leaf! "lookup" 1 native-lookup)
(native-env-leaf! "put_key" 2 native-env-put!)
(native-env-leaf! "delete_key" 1 (lambda (key)
 (set! native-env-rows (native-map-remove native-env-rows key)) (native-env-row-changed! key) (bl-key "ok")))
(native-env-leaf! "intern" 3 native-intern)
(native-env-leaf! "fetch" 2 native-fetch)
(native-env-leaf! "fetch!" 2 native-fetch!)
(native-env-leaf! "peek" 2 native-fetch)
(native-env-leaf! "fetch_exact" 2 (lambda (ns name) (native-fetch ns name #t)))
(native-env-leaf! "fetch_exact!" 2 (lambda (ns name) (native-fetch! ns name #t)))
(native-env-leaf! "bound?" 2 (lambda (ns name) (not (eq? (native-fetch ns name) (bl-key "error")))))
(native-env-leaf! "local_var?" 2 native-local-var?)
(native-env-leaf! "link" 2 (lambda (ns name) (native-env-link ns name #f)))
(native-env-leaf! "link_owner" 2 (lambda (ns name) (native-env-link ns name #t)))
(native-env-leaf! "put_link" 3 (lambda (ns name info) (native-env-put! (native-row (bl-key "link") ns name) info)))
(native-env-leaf! "current_ns" 0 (lambda () native-env-current))
(native-env-leaf! "in_ns" 1 native-in-ns)
(native-env-leaf! "declare_ns" 1 native-declare-ns)
(native-env-leaf! "mark_loaded" 1 native-declare-ns)
(native-env-leaf! "ns_exists?" 1 native-known-ns?)
(native-env-leaf! "loaded_ns?" 1 native-known-ns?)
(native-env-leaf! "meta" 2 native-meta)
(native-env-leaf! "put_meta" 3 native-put-meta)
(native-env-leaf! "env_id" 0 (lambda () (list (bl-key "global"))))
(native-env-leaf! "doc_string" 2 (lambda (ns name)
 (let ((meta (native-meta ns name)))
  (if (eq? meta (bl-key "error")) bl-nil (bl-get (bl-nth meta 1) (bl-key "doc"))))))
(native-env-leaf! "add_core_excludes" 2 (lambda (ns names)
 (if (not (native-list? names)) (error "core excludes must be a proper list")
  (native-env-put! (native-row (bl-key "refer_clojure_exclude") ns) names))))
(native-env-leaf! "core_excludes" 1 (lambda (ns)
 (bl-get native-env-rows (native-row (bl-key "refer_clojure_exclude") ns) '())))
(native-env-leaf! "caps" 0 (lambda () (bl-key "all")))
(native-env-leaf! "caps_allowed?" 2 (lambda (module op) #t))
(native-env-leaf! "op_of" 2 (lambda (module fn) bl-nil))
(for-each (lambda (row)
 (let ((tag (car row)) (put (cadr row)) (get (caddr row)))
  (native-env-leaf! put 3 (lambda (ns name target) (native-env-put! (native-row (bl-key tag) ns name) target)))
  (native-env-leaf! get 2 (lambda (ns name)
   (let ((v (native-env-value (native-row (bl-key tag) ns name)))) (if (eq? v native-missing) bl-nil v))))))
 '(("alias" "add_alias" "alias_target") ("refer" "add_refer" "refer_source") ("import" "add_import" "import_target")))
(native-add-leaf! "host/eval-scheme/1" native-eval-string)
;; This finite emission boundary calls the actual compiled BL emitter.
;; The Scheme profile needs no direct-C namespace and never interprets ANF.
(define (native-eval-node-scheme node context)
 (native-eval-string
  (bl-invoke (native-global-exact "native.scheme" "emit") (list node context))))
(native-add-leaf! "host/eval-node/2" native-eval-node-scheme)

(native-add-leaf! "host/read-file/1" native-read-file)
(native-add-leaf! "host/write-file/2" native-write-file)
(native-add-leaf! "host/command-line/0" native-command-line)
(for-each (lambda (name)
 (native-add-leaf! (string-append "Elixir.BeamLisp.Loader/" name "/1") native-ensure-loaded))
 '("ensure_loaded" "ensure_ready" "load_provider"))
(native-add-leaf! "Elixir.BeamLisp.Loader/resolvable?/1" native-known-ns?)
(native-add-leaf! "Elixir.BeamLisp.Loader/declare_require/3" (lambda (ns alias refers) (native-ensure-loaded ns)))
;; All admitted source providers are already present. A macro probe of a raw
;; foreign module is not a request to load a language namespace (loader.bl1680).
(define (native-maybe-load-macro ns name)
 (if (not (native-known-ns? ns)) #f
  (let ((answer (native-fetch ns name #t)))
   (and (not (eq? answer (bl-key "error")))
    (let ((value (bl-nth answer 1)))
     (and (bl-tag? value 'tuple) (= 2 (bl-count value))
          (eq? (bl-nth value 0) (bl-key "$macro"))))))))
(native-add-leaf! "Elixir.BeamLisp.Loader/maybe_load_macro/2" native-maybe-load-macro)
(native-add-leaf! "Elixir.BeamLisp.Loader/source_decl/2" (lambda (ns name) bl-nil))

;; Finite ETS match-pattern subset over the actual registry rows. These are
;; compiler metadata queries, never an ETS/process ownership implementation.
(define (native-pattern-var pattern)
 (and (native-keyword? pattern)
  (let ((s (native-atom-name pattern)))
   (and (> (string-length s) 1) (char=? (string-ref s 0) #\$)
    (string->number (substring s 1 (string-length s)))))))
(define (native-row-match pattern value bindings)
 (cond
  ((eq? pattern (bl-key "_")) bindings)
  ((native-pattern-var pattern)
   => (lambda (index)
       (let ((previous (bl-get bindings index native-missing)))
        (if (eq? previous native-missing) (bl-assoc bindings index value)
         (and (bl-equal? previous value) bindings)))))
  ((and (bl-tag? pattern 'tuple) (bl-tag? value 'tuple) (= (bl-count pattern) (bl-count value)))
   (let loop ((ps (bl-items pattern)) (vs (bl-items value)) (bindings bindings))
    (cond ((not bindings) #f) ((null? ps) bindings)
     (else (loop (cdr ps) (cdr vs) (native-row-match (car ps) (car vs) bindings))))))
  ((and (pair? pattern) (pair? value))
   (let ((next (native-row-match (car pattern) (car value) bindings)))
    (and next (native-row-match (cdr pattern) (cdr value) next))))
  ((bl-equal? pattern value) bindings) (else #f)))
(define (native-env-match pattern)
 (let loop ((rows (native-map-pairs native-env-rows)) (out '()))
  (if (null? rows) (reverse out)
   (let ((bindings (native-row-match pattern (car rows) (bl-empty-map))))
    (loop (cdr rows)
     (if bindings (cons (map (lambda (entry) (bl-nth entry 1)) (native-map-pairs bindings)) out) out))))))
(native-env-leaf! "match" 1 native-env-match)
(define (native-public-names ns)
 (let ((prefix (string-append ns "/")))
  (let loop ((rows (native-map-pairs native-global-registry)) (out '()))
   (if (null? rows) out
    (let* ((key (bl-nth (car rows) 0)) (len (string-length prefix)))
     (if (and (>= (string-length key) len) (string=? prefix (substring key 0 len)))
      (let* ((name (substring key len (string-length key))) (meta (native-meta ns name)))
       (loop (cdr rows)
        (if (and (not (eq? meta (bl-key "error"))) (eq? #t (bl-get (bl-nth meta 1) (bl-key "private")))) out (cons name out))))
      (loop (cdr rows) out)))))))
(native-env-leaf! "public_names" 1 native-public-names)
(native-env-leaf! "add_refer_all" 2 (lambda (ns source)
 (native-ensure-loaded source)
 (for-each (lambda (name) (native-env-put! (native-row (bl-key "refer") ns name) source)) (native-public-names source))
 (bl-key "ok")))

(define (native-unavailable key)
 (lambda arguments (error "native compiler excludes BEAM Source custody" key)))
(for-each (lambda (row)
 (let ((key (string-append "Elixir.BeamLisp.Env/" (car row) "/" (number->string (cadr row)))))
  (native-add-leaf! key (native-unavailable key))))
 '(("check_source_callable!" 1) ("check_source_invocation!" 2)
   ("check_source_invocation1!" 2) ("check_source_invocation2!" 3)
   ("assert_native_framework_execution!" 0)))
(native-add-leaf! "Elixir.BeamLisp.Server/return_constructor_shapes/0"
 (lambda () (bl-get native-bundle-metadata (bl-key "return-constructor-shapes"))))
(native-add-leaf! "Elixir.BeamLisp.Tiers/boot_namespaces/0"
 (lambda () '("anf" "compiler" "core" "diag" "lower" "optimize" "reader" "reader-node" "rt" "sugar")))
(define (native-known-module ns)
 (let ((captured (bl-get native-namespace-modules ns native-missing)))
  (if (not (eq? captured native-missing)) captured
   ; Same unqualified platform spelling as Emit/base_module_for and the JS
   ; moduleFor adapter: one CamelCased alias segment per dot-separated part.
   ; Existing realm identities ALWAYS use the captured table above.
   (bl-key
    (string-append "Elixir.BeamLisp.Ns."
     (list->string
      (let loop ((chars (string->list ns)) (upper? #t) (out '()))
       (if (null? chars) (reverse out)
        (let ((ch (car chars)))
         (cond ((char=? ch #\_) (loop (cdr chars) #t out))
               ((char=? ch #\.) (loop (cdr chars) #t (cons ch out)))
               (else (loop (cdr chars) #f (cons (if upper? (char-upcase ch) ch) out)))))))))))))
(native-add-leaf! "Elixir.BeamLisp.Link/module_for/1" native-known-module)
(native-add-leaf! "Elixir.BeamLisp.Emit/module_for/1" native-known-module)
(native-add-leaf! "Elixir.BeamLisp.Emit/base_module_for/1" native-known-module)
(native-add-leaf! "Elixir.BeamLisp.Link/settle/0" (lambda () (bl-key "ok")))
(native-add-leaf! "erlang/function_exported/3" native-remote-available?)

;; The canonical compiler's host facade delegates read_data directly to the
;; SAME compiler namespace; parsing and datum conversion stay in compiled BL.
(native-add-leaf! "Elixir.BeamLisp.Compiler/read_data/1"
 (lambda (source) (bl-invoke (native-global "compiler" "read_data") (list source))))

;; Native symbol accounting. The BEAM table watermark has no native table to
;; query; bound new source names explicitly instead. Existing names cost zero.
(define native-source-symbols (bl-empty-map))
(define native-source-symbol-count 0)
(define native-source-symbol-bytes 0)
(define native-source-symbol-limit 65536)
(define native-source-symbol-byte-limit 16777216)
(define native-reader-symbol-count 0)
(define (native-atom-check token)
 (if (and (string? token) (> (length (native-utf8-bytes token)) 1048576))
  (error "native symbol token exceeds one MiB"))
 (if (or (> native-source-symbol-count native-source-symbol-limit)
         (> native-source-symbol-bytes native-source-symbol-byte-limit))
  (error "native symbol budget exceeded"))
 (bl-key "ok"))
(define (native-atom-account token)
 (native-atom-check token)
 (set! native-reader-symbol-count (+ native-reader-symbol-count 1))
 (if (and (string? token) (not (native-map-has? native-source-symbols token)))
  (begin
   (set! native-source-symbols (bl-assoc native-source-symbols token #t))
   (set! native-source-symbol-count (+ native-source-symbol-count 1))
   (set! native-source-symbol-bytes (+ native-source-symbol-bytes (length (native-utf8-bytes token))))
   (native-atom-check token)))
 (bl-key "ok"))
(native-add-leaf! "Elixir.BeamLisp.AtomGuard/check!/1" native-atom-check)
(native-add-leaf! "Elixir.BeamLisp.AtomGuard/account!/1" native-atom-account)
(native-add-leaf! "Elixir.BeamLisp.AtomGuard/reset/0" (lambda () (set! native-reader-symbol-count 0) (bl-key "ok")))
(native-add-leaf! "Elixir.BeamLisp.AtomGuard/to_atom/1"
 (lambda (text) (if (not (string? text)) (error "native atom requires text")
  (begin (native-atom-account text) (bl-key text)))))

;; Target exception representation is the same tagged data exposed to BL.
;; Raise/class/trace transport is supplied by host-values.scm.
(define (native-ex-info message data)
 (bl-map (bl-key "__struct__") (bl-key "Elixir.BeamLisp.ExInfo")
         (bl-key "__exception__") #t (bl-key "message") message (bl-key "data") data))
(define (native-exception-value? x)
 (and (bl-tag? x 'map) (native-keyword? (bl-get x (bl-key "__struct__")))
      (native-map-has? x (bl-key "__exception__"))))
(native-add-leaf! "Elixir.BeamLisp.ExInfo/ex_info/2" native-ex-info)
(native-add-leaf! "Elixir.BeamLisp.ExInfo/ex_data/1"
 (lambda (x) (if (eq? (native-struct-module x) (bl-key "Elixir.BeamLisp.ExInfo")) (bl-get x (bl-key "data")) bl-nil)))
(native-add-leaf! "Elixir.BeamLisp.ExInfo/ex_message/1"
 (lambda (x) (if (native-exception-value? x) (bl-get x (bl-key "message")) (bl-show x))))
(native-add-leaf! "Elixir.BeamLisp.ExInfo/ex_original/1"
 (lambda (x) (if (eq? (native-struct-module x) (bl-key "Elixir.ErlangError")) (bl-get x (bl-key "original")) bl-nil)))
(native-add-leaf! "Elixir.BeamLisp.ExInfo/raise_payload/1"
 (lambda (x)
  (native-raise (bl-key "error")
   (cond ((native-exception-value? x) x)
         ((bl-tag? x 'map) (native-ex-info (bl-invoke (native-global "rt" "print_str") (list x)) x))
         (else (native-ex-info (bl-show x) bl-nil)))
   (native-capture-stack))))

;; Closed record registry; declaration/publication APIs require the BEAM's
;; Source custody and remain explicit exclusions, just as in the JS target.
(define native-record-descriptors (bl-empty-map))
(native-add-leaf! "Elixir.BeamLisp.Record/info/1" (lambda (module) (bl-get native-record-descriptors module)))
(native-add-leaf! "Elixir.BeamLisp.Record/record_module?/1" (lambda (module)
 (let ((info (bl-get native-record-descriptors module)))
  (and (bl-tag? info 'tuple) (= (bl-count info) 4) (eq? (bl-nth info 0) (bl-key "record"))))))
(native-add-leaf! "Elixir.BeamLisp.Record/deftype_module?/1" (lambda (module)
 (let ((info (bl-get native-record-descriptors module)))
  (and (bl-tag? info 'tuple) (= (bl-count info) 4) (eq? (bl-nth info 0) (bl-key "deftype"))))))
(native-add-leaf! "Elixir.BeamLisp.Record/record?/1" (lambda (value)
 (bl-invoke (native-remote "Elixir.BeamLisp.Record/record_module?/1") (list (native-struct-module value)))))
(native-add-leaf! "Elixir.BeamLisp.Record/fields_of/1" (lambda (module)
 (let ((info (bl-get native-record-descriptors module)))
  (if (bl-is-nil info) (error "not a beam-lisp record/deftype" module) (bl-nth info 3)))))
(native-add-leaf! "Elixir.BeamLisp.Server/callback/1" (lambda (name)
 (let ((row (assoc name '(("init" "init" 1 "vector") ("handle-call" "handle_call" 3 "pattern")
                         ("handle-cast" "handle_cast" 2 "pattern") ("handle-info" "handle_info" 2 "pattern")
                         ("handle-continue" "handle_continue" 2 "vector") ("terminate" "terminate" 2 "vector")))))
  (if row (bl-tuple (list (bl-key (cadr row)) (caddr row) (bl-key (cadddr row)))) bl-nil))))
(native-add-leaf! "Elixir.BeamLisp.Server/callback_order/0"
 (lambda () (map bl-key '("init" "handle_call" "handle_cast" "handle_info" "handle_continue" "terminate" "code_change"))))
(native-add-leaf! "Elixir.BeamLisp.Server/module_for/2" (lambda (ns name)
 (let* ((base (native-atom-name (native-known-module (string-append ns "." name))))
        (prefix "Elixir.BeamLisp.Ns."))
  (bl-key (string-append "Elixir.BeamLisp.Server." (substring base (string-length prefix) (string-length base)))))))

;; These same execution/metadata seams are named BEAM-only refusals by the
;; production JS host. Never pretend their registration grants capability.
(define native-beam-only-leaves
 '("Elixir.BeamLisp.AOT/constructor_metadata_compiling?/0"
   "Elixir.BeamLisp.AOT/constructor_call!/5"
   "Elixir.BeamLisp.AOT/sdk_constructor_binding_reference/2"
   "Elixir.BeamLisp.AOT/sdk_constructor_declaration_kind/2"
   "Elixir.BeamLisp.AOT/sdk_declaration_kind/2"
   "Elixir.BeamLisp.AOT/staged_macro_kind/2"
   "Elixir.BeamLisp.AOT/staged_macro_lookup/2"
   "Elixir.BeamLisp.Record/declaration_descriptor/4"
   "Elixir.BeamLisp.Record/declaration_descriptor/5"
   "Elixir.BeamLisp.Record/declaration_kind/3"
   "Elixir.BeamLisp.Trace/trace/3" "Elixir.BeamLisp.Trace/trace/4" "Elixir.BeamLisp.Trace/untrace/2"
   "Elixir.BeamLisp.Refs/spawn_exec/1" "Elixir.BeamLisp.Refs/spawn_exec/2"
   "erlang/term_to_binary/2" "erlang/binary_to_term/2"
   "Elixir.Code/ensure_loaded?/1" "crypto/hash/2" "Elixir.Base/encode16/1" "Elixir.Base/encode16/2"
   "Elixir.BeamLisp.Env/os_env_call/2" "erlang/monitor/2" "erlang/exit/2"))
(define native-beam-seed-only-leaves
 '("Elixir.BeamLisp.Supervisor/supervise/2" "Elixir.BeamLisp.Supervisor/supervise/3"
   "Elixir.BeamLisp.Supervisor/worker/2" "Elixir.BeamLisp.Supervisor/worker/3"
   "Elixir.BeamLisp.Server/start/1" "Elixir.BeamLisp.Server/start/2" "Elixir.BeamLisp.Server/start/3"
   "Elixir.BeamLisp.Server/start_link/1" "Elixir.BeamLisp.Server/start_link/2" "Elixir.BeamLisp.Server/start_link/3"
   "Elixir.BeamLisp.Server/call/2" "Elixir.BeamLisp.Server/call/3" "Elixir.BeamLisp.Server/cast/2"
   "Elixir.BeamLisp.Server/stop/1" "Elixir.BeamLisp.Server/stop/2" "erlang/link/1"
   "Elixir.BeamLisp.Refs/future_cancel/1"))
(set! native-beam-only-leaves (append native-beam-only-leaves native-beam-seed-only-leaves))
(set! native-excluded-host-leaves (append native-excluded-host-leaves native-beam-only-leaves))
(for-each (lambda (key) (native-add-leaf! key (native-unavailable key))) native-beam-only-leaves)
