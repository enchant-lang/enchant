;; Erlang/Elixir BIFs the DATA host modules call (category b), named exactly
;; as their BEAM counterparts. Loaded after host-compiler.scm.

;; erlang:error/2 raises Reason with class error; the argument list is only
;; stack decoration on BEAM. Delegate to the live error/1 leaf so a transport
;; rebinding of erlang/error/1 (host-source-frames.scm) applies to both.
(native-add-leaf! "erlang/error/2" (lambda (reason args) (bl-invoke (native-leaf "erlang/error/1") (list reason))))

;; erlang:fun_info/2 is NOT defined here: the main thread adds its one native
;; leaf at integration. See speed/data/RESULT.md for what these modules need
;; from it (the self-module idiom (erlang/fun_info (fn [] nil) :module)).

;; ── Elixir stdlib exceptions (defexception structs) ──────────────────────
;; Exception structs are maps tagged :__struct__ with :__exception__ true and
;; exactly the fields the Elixir defexception declares; exception/1 folds a
;; keyword list over the defaults (an undeclared key is a KeyError, as
;; Kernel.struct!/2 raises).
(define (native-nil-defaults names) (map (lambda (n) (cons n bl-nil)) names))
(define (native-exception-struct module fields opts)
 (let loop ((ps (native-assert-list opts))
            (m (let build ((fs fields) (m (bl-map (bl-key "__struct__") (bl-key module) (bl-key "__exception__") #t)))
                (if (null? fs) m (build (cdr fs) (bl-assoc m (bl-key (caar fs)) (cdar fs)))))))
  (if (null? ps) m
   (let ((p (car ps)))
    (if (not (and (bl-tag? p 'tuple) (= 2 (bl-count p)) (native-map-has? m (bl-nth p 0))))
     (native-raise (bl-key "error")
      (native-exception-struct "Elixir.KeyError" (native-nil-defaults '("key" "term" "message"))
       (list (bl-make-tuple (bl-key "key") (if (bl-tag? p 'tuple) (bl-nth p 0) p))))
      (native-capture-stack))
     (loop (cdr ps) (bl-assoc m (bl-nth p 0) (bl-nth p 1))))))))
;; KeyError: defexception [:key, :term, :message].
(native-add-leaf! "Elixir.KeyError/exception/1"
 (lambda (opts) (native-exception-struct "Elixir.KeyError" (native-nil-defaults '("key" "term" "message")) opts)))
;; CaseClauseError: defexception [:term].
(native-add-leaf! "Elixir.CaseClauseError/exception/1"
 (lambda (opts) (native-exception-struct "Elixir.CaseClauseError" (native-nil-defaults '("term")) opts)))

;; Kernel.inspect/1 for the terms Elixir's exception messages embed: a
;; keyword list prints in keyword syntax ([file: "a.bl"]); everything else is
;; the host's Kernel/inspect leaf. Pretty-printing line breaks of terms wider
;; than 98 columns are not reproduced.
(define (native-keyword-list? xs)
 (and (pair? xs) (native-list? xs)
      (let loop ((xs xs)) (or (null? xs) (and (bl-tag? (car xs) 'tuple) (= 2 (bl-count (car xs)))
                                              (native-keyword? (bl-nth (car xs) 0)) (loop (cdr xs)))))))
(define (native-elixir-inspect x)
 (if (native-keyword-list? x)
  (string-append "["
   (let loop ((xs x) (out ""))
    (if (null? xs) out
     (loop (cdr xs) (string-append out (if (string=? out "") "" ", ")
                     (native-atom-name (bl-nth (car xs) 0)) ": " (native-elixir-inspect (bl-nth (car xs) 1))))))
   "]")
  (native-erlang-inspect x)))
;; Exception.message/1: the module's own message/1 when one is linked (a
;; leaf or a compiled host module), else the generated callbacks of the two
;; stdlib structs above, else the :message field. A non-binary result is
;; reported the way Elixir reports it.
(define (native-exception-message e)
 (if (not (native-exception-value? e))
  (native-raise (bl-key "error") (bl-key "function_clause") (native-capture-stack))
  (let* ((module (bl-get e (bl-key "__struct__"))) (name (native-atom-name module))
         (result
          (cond ((native-remote-available? module (bl-key "message") 1)
                 (bl-invoke (native-remote (string-append name "/message/1")) (list e)))
                ((and (string=? name "Elixir.KeyError") (bl-is-nil (bl-get e (bl-key "message"))))
                 (let ((term (bl-get e (bl-key "term"))))
                  (string-append "key " (native-erlang-inspect (bl-get e (bl-key "key"))) " not found"
                   (if (bl-is-nil term) ""
                    (string-append " in:\n\n    " (native-elixir-inspect term) "\n")))))
                ((and (string=? name "Elixir.ErlangError") (bl-is-nil (bl-get e (bl-key "message") bl-nil)))
                 (string-append "Erlang error: " (native-elixir-inspect (bl-get e (bl-key "original")))))
                ((string=? name "Elixir.CaseClauseError")
                 (string-append "no case clause matching: " (native-erlang-inspect (bl-get e (bl-key "term")))))
                (else (bl-get e (bl-key "message") bl-nil)))))
   (if (string? result) result
    (string-append "got " (native-erlang-inspect result)
     " while retrieving Exception.message/1 for " (native-erlang-inspect e) " (expected a string)")))))
(native-add-leaf! "Elixir.Exception/message/1" native-exception-message)

;; ── Keyword (lists:keyfind/3 on position 1) ──────────────────────────────
(define (native-keyword-find kw key)
 (let loop ((xs kw))
  (cond ((not (pair? xs)) #f)
        ((and (bl-tag? (car xs) 'tuple) (>= (bl-count (car xs)) 1) (native-erlang-equal? (bl-nth (car xs) 0) key)) (car xs))
        (else (loop (cdr xs))))))
(define (native-keyword-guard! kw key)
 (if (not (and (or (null? kw) (pair? kw)) (native-keyword? key)))
  (native-raise (bl-key "error") (bl-key "function_clause") (native-capture-stack))))
(native-add-leaf! "Elixir.Keyword/get/2"
 (lambda (kw key) (native-keyword-guard! kw key)
  (let ((p (native-keyword-find kw key))) (if p (bl-nth p 1) bl-nil))))
(native-add-leaf! "Elixir.Keyword/fetch!/2"
 (lambda (kw key) (native-keyword-guard! kw key)
  (let ((p (native-keyword-find kw key)))
   (if p (bl-nth p 1)
    (native-raise (bl-key "error")
     (native-exception-struct "Elixir.KeyError" (native-nil-defaults '("key" "term" "message"))
      (list (bl-make-tuple (bl-key "key") key) (bl-make-tuple (bl-key "term") kw)))
     (native-capture-stack))))))

;; String.Chars.to_string/1: the protocol's Atom/BitString/Integer/Float/List
;; implementations. host-extra.scm's native-vector-index-text is exactly that
;; dispatch, Protocol.UndefinedError included.
(native-add-leaf! "Elixir.String.Chars/to_string/1" native-vector-index-text)

;; ── cerl: Core Erlang trees as data (OTP compiler-10.0.1 cerl.erl) ───────
;; lower/lower-core build Core through OTP's cerl module. Each leaf builds or
;; reads exactly the record tuple cerl builds; field order and defaults are
;; core_parse.hrl's: every record is {Tag, Anno, Fields...} with Anno = [].
;; The folds are cerl's own: c_cons/c_tuple of literals give a c_literal,
;; c_map over literal pairs gives a literal map. Record reads raise
;; {badrecord, Node} as OTP 26+ field access does; type/1 of anything else
;; raises function_clause.
(define (cerl-raise reason) (native-raise (bl-key "error") reason (native-capture-stack)))
(define (cerl-function-clause) (cerl-raise (bl-key "function_clause")))
(define cerl-type-rows
 (map (lambda (row) (list (bl-key (car row)) (cadr row) (bl-key (caddr row))))
  '(("c_alias" 4 "alias") ("c_apply" 4 "apply") ("c_binary" 3 "binary") ("c_bitstr" 7 "bitstr")
    ("c_call" 5 "call") ("c_case" 4 "case") ("c_catch" 3 "catch") ("c_clause" 5 "clause")
    ("c_cons" 4 "cons") ("c_fun" 4 "fun") ("c_let" 5 "let") ("c_letrec" 4 "letrec")
    ("c_literal" 3 "literal") ("c_map" 5 "map") ("c_map_pair" 5 "map_pair") ("c_module" 6 "module")
    ("c_primop" 4 "primop") ("c_receive" 5 "receive") ("c_seq" 4 "seq") ("c_record" 5 "record")
    ("c_record_pair" 4 "record_pair") ("c_try" 7 "try") ("c_tuple" 3 "tuple") ("c_values" 3 "values")
    ("c_var" 3 "var") ("c_opaque" 3 "opaque"))))
(define (cerl-tag name) (car (let find ((rows cerl-type-rows))
                              (if (eq? (car (car rows)) (bl-key name)) (car rows) (find (cdr rows))))))
(define cerl-tag-literal (cerl-tag "c_literal"))
(define cerl-tag-var (cerl-tag "c_var"))
(define cerl-tag-clause (cerl-tag "c_clause"))
(define cerl-tag-let (cerl-tag "c_let"))
(define cerl-tag-map-pair (cerl-tag "c_map_pair"))
(define (cerl-record? x tag size)
 (and (bl-tag? x 'tuple) (= (bl-count x) size) (eq? (bl-nth x 0) tag)))
(define (cerl-node tag . fields) (bl-tuple (cons tag (cons '() fields))))
(define (cerl-literal v) (cerl-node cerl-tag-literal v))
(define (cerl-literal? x) (cerl-record? x cerl-tag-literal 3))
(define (cerl-field node tag size index)
 (if (cerl-record? node tag size) (bl-nth node index)
  (cerl-raise (bl-tuple (list (bl-key "badrecord") node)))))
;; is_lit_list/1 and lit_list_vals/1: a proper list, else function_clause.
(define (cerl-lit-list? es)
 (cond ((null? es) #t) ((pair? es) (and (cerl-literal? (car es)) (cerl-lit-list? (cdr es))))
       (else (cerl-function-clause))))
(define (cerl-lit-vals es) (map (lambda (e) (bl-nth e 2)) es))
(define (cerl-atom? x) (or (native-keyword? x) (boolean? x) (bl-is-nil x)))
;; c_atom(Name) of a non-atom is list_to_atom(Name): a code-point list.
(define (cerl-list-to-atom xs)
 (if (and (native-list? xs)
          (let check ((xs xs)) (or (null? xs) (and (integer? (car xs)) (exact? (car xs)) (>= (car xs) 0)
                                                    (< (car xs) 1114112) (not (and (>= (car xs) 55296) (< (car xs) 57344)))
                                                    (check (cdr xs))))))
  (bl-key (list->string (map integer->char xs)))
  (cerl-raise (bl-key "badarg"))))
(define (cerl-c-atom name) (cerl-literal (if (cerl-atom? name) name (cerl-list-to-atom name))))
(define (cerl-c-var name) (cerl-node cerl-tag-var name))
(define (cerl-c-tuple es)
 (if (cerl-lit-list? es) (cerl-literal (bl-tuple (cerl-lit-vals es))) (cerl-node (cerl-tag "c_tuple") es)))
(define (cerl-c-cons head tail)
 (if (and (cerl-literal? head) (cerl-literal? tail))
  (cerl-literal (cons (bl-nth head 2) (bl-nth tail 2)))
  (cerl-node (cerl-tag "c_cons") head tail)))
;; update_map_literal/2: the literal map, or #f where cerl answers none.
(define (cerl-op-pair? pair op)
 (and (cerl-record? pair cerl-tag-map-pair 5)
      (let ((o (bl-nth pair 2))) (and (cerl-literal? o) (eq? (bl-nth o 2) (bl-key op))))))
(define (cerl-update-map-literal es m)
 (cond ((null? es) m)
  ((not (pair? es)) (cerl-function-clause))
  (else
   (let ((pair (car es)))
    (cond ((cerl-op-pair? pair "assoc")
           (if (cerl-lit-list? (list (bl-nth pair 3) (bl-nth pair 4)))
            (cerl-update-map-literal (cdr es) (native-raw-map-put (bl-nth (bl-nth pair 3) 2) (bl-nth (bl-nth pair 4) 2) m))
            #f))
          ((cerl-op-pair? pair "exact")
           (if (cerl-lit-list? (list (bl-nth pair 3) (bl-nth pair 4)))
            (if (native-raw-map-has? m (bl-nth (bl-nth pair 3) 2))
             (cerl-update-map-literal (cdr es) (native-raw-map-put (bl-nth (bl-nth pair 3) 2) (bl-nth (bl-nth pair 4) 2) m))
             #f)
            #f))
          (else (cerl-function-clause)))))))
;; ann_c_map([], Arg, Es): a literal map argument folds when every pair does.
(define (cerl-c-map-update arg es)
 (let ((folded (and (cerl-literal? arg) (bl-truthy (bl-invoke (native-leaf "erlang/is_map/1") (list (bl-nth arg 2)))) (cerl-update-map-literal es (bl-nth arg 2)))))
  (if folded (cerl-literal folded) (cerl-node (cerl-tag "c_map") arg es #f))))
(define (cerl-empty-map-literal) (cerl-literal (bl-empty-map)))
(define (cerl-c-bitstr val size unit type flags) (cerl-node (cerl-tag "c_bitstr") val size unit type flags))
(define (cerl-c-clause pats guard body) (cerl-node cerl-tag-clause pats guard body))
(define (cerl-c-receive clauses timeout action) (cerl-node (cerl-tag "c_receive") clauses timeout action))
(define (cerl-c-module name exports attrs defs) (cerl-node (cerl-tag "c_module") name exports attrs defs))
(native-add-leaf! "cerl/abstract/1" cerl-literal)
(native-add-leaf! "cerl/c_atom/1" cerl-c-atom)
(native-add-leaf! "cerl/c_var/1" cerl-c-var)
(native-add-leaf! "cerl/c_fname/2" (lambda (atom arity) (cerl-c-var (bl-make-tuple atom arity))))
(native-add-leaf! "cerl/c_nil/0" (lambda () (cerl-literal '())))
(native-add-leaf! "cerl/c_cons/2" cerl-c-cons)
(native-add-leaf! "cerl/c_tuple/1" cerl-c-tuple)
(native-add-leaf! "cerl/c_values/1" (lambda (es) (cerl-node (cerl-tag "c_values") es)))
(native-add-leaf! "cerl/c_alias/2" (lambda (var pattern) (cerl-node (cerl-tag "c_alias") var pattern)))
(native-add-leaf! "cerl/c_apply/2" (lambda (op args) (cerl-node (cerl-tag "c_apply") op args)))
(native-add-leaf! "cerl/c_call/3" (lambda (module name args) (cerl-node (cerl-tag "c_call") module name args)))
(native-add-leaf! "cerl/c_primop/2" (lambda (name args) (cerl-node (cerl-tag "c_primop") name args)))
(native-add-leaf! "cerl/c_case/2" (lambda (arg clauses) (cerl-node (cerl-tag "c_case") arg clauses)))
(native-add-leaf! "cerl/c_clause/2" (lambda (pats body) (cerl-c-clause pats (cerl-c-atom #t) body)))
(native-add-leaf! "cerl/c_clause/3" cerl-c-clause)
(native-add-leaf! "cerl/c_fun/2" (lambda (vars body) (cerl-node (cerl-tag "c_fun") vars body)))
(native-add-leaf! "cerl/c_let/3" (lambda (vars arg body) (cerl-node cerl-tag-let vars arg body)))
(native-add-leaf! "cerl/c_letrec/2" (lambda (defs body) (cerl-node (cerl-tag "c_letrec") defs body)))
(native-add-leaf! "cerl/c_seq/2" (lambda (arg body) (cerl-node (cerl-tag "c_seq") arg body)))
(native-add-leaf! "cerl/c_try/5"
 (lambda (arg vars body evars handler) (cerl-node (cerl-tag "c_try") arg vars body evars handler)))
(native-add-leaf! "cerl/c_receive/1"
 (lambda (clauses) (cerl-c-receive clauses (cerl-c-atom (bl-key "infinity")) (cerl-c-atom #t))))
(native-add-leaf! "cerl/c_receive/3" cerl-c-receive)
(native-add-leaf! "cerl/c_binary/1" (lambda (segments) (cerl-node (cerl-tag "c_binary") segments)))
(native-add-leaf! "cerl/c_bitstr/5" cerl-c-bitstr)
(native-add-leaf! "cerl/c_bitstr/4"
 (lambda (val size type flags) (cerl-c-bitstr val size (cerl-literal 1) type flags)))
(native-add-leaf! "cerl/c_bitstr/3"
 (lambda (val type flags) (cerl-c-bitstr val (cerl-literal (bl-key "all")) (cerl-literal 1) type flags)))
(native-add-leaf! "cerl/c_map/1" (lambda (pairs) (cerl-c-map-update (cerl-empty-map-literal) pairs)))
(native-add-leaf! "cerl/c_map/2" cerl-c-map-update)
(native-add-leaf! "cerl/c_map_pattern/1"
 (lambda (pairs) (cerl-node (cerl-tag "c_map") (cerl-empty-map-literal) pairs #t)))
(native-add-leaf! "cerl/c_map_pair/2"
 (lambda (key val) (cerl-node cerl-tag-map-pair (cerl-literal (bl-key "assoc")) key val)))
(native-add-leaf! "cerl/c_map_pair_exact/2"
 (lambda (key val) (cerl-node cerl-tag-map-pair (cerl-literal (bl-key "exact")) key val)))
(native-add-leaf! "cerl/c_module/3" (lambda (name exports defs) (cerl-c-module name exports '() defs)))
(native-add-leaf! "cerl/c_module/4" cerl-c-module)
(native-add-leaf! "cerl/clause_pats/1" (lambda (node) (cerl-field node cerl-tag-clause 5 2)))
(native-add-leaf! "cerl/clause_guard/1" (lambda (node) (cerl-field node cerl-tag-clause 5 3)))
(native-add-leaf! "cerl/clause_body/1" (lambda (node) (cerl-field node cerl-tag-clause 5 4)))
(native-add-leaf! "cerl/let_vars/1" (lambda (node) (cerl-field node cerl-tag-let 5 2)))
(native-add-leaf! "cerl/let_arg/1" (lambda (node) (cerl-field node cerl-tag-let 5 3)))
(native-add-leaf! "cerl/let_body/1" (lambda (node) (cerl-field node cerl-tag-let 5 4)))
(native-add-leaf! "cerl/var_name/1" (lambda (node) (cerl-field node cerl-tag-var 3 2)))
;; get_ann/1 and set_ann/2 are element(2, Node) and setelement(2, Node, List).
(native-add-leaf! "cerl/get_ann/1" (lambda (node) (bl-invoke (native-leaf "erlang/element/2") (list 2 node))))
(native-add-leaf! "cerl/set_ann/2"
 (lambda (node anno) (bl-invoke (native-leaf "erlang/setelement/3") (list 2 node anno))))
(native-add-leaf! "cerl/update_c_let/4"
 (lambda (node vars arg body)
  (bl-tuple (list cerl-tag-let (bl-invoke (native-leaf "erlang/element/2") (list 2 node)) vars arg body))))
(native-add-leaf! "cerl/type/1"
 (lambda (node)
  (let find ((rows cerl-type-rows))
   (cond ((null? rows) (cerl-function-clause))
    ((cerl-record? node (car (car rows)) (cadr (car rows))) (caddr (car rows)))
    (else (find (cdr rows)))))))
;; lists:usort/1 (lower's local-loop parameter check): term order, stable,
;; keeping the first of each run of == elements.
(native-add-leaf! "lists/usort/1"
 (lambda (xs)
  (let loop ((xs (native-sort native-term-le (native-assert-list xs))) (out '()))
   (cond ((null? xs) (reverse out))
    ((and (pair? out) (= 0 (native-term-compare (car out) (car xs)))) (loop (cdr xs) out))
    (else (loop (cdr xs) (cons (car xs) out)))))))

;; ── External term format (ETF), version 131 ───────────────────────────────
;; term_to_binary/binary_to_term over the native value model. Atoms: #t, #f
;; and nil are true/false/nil; colon symbols and UTF16 keyword wrappers carry
;; their names. Text binaries are Scheme strings (UTF-8 on the wire); bytes
;; that are not UTF-8 text are a host byte value #(bytes BYTEVECTOR), which
;; only these leaves and host/read-bytes, host/write-bytes accept. Vectors,
;; sets and opaque structs travel as the struct maps BEAM holds for them, and
;; decode back to the native value. Maps are written in term order (the
;; :deterministic order); binary_to_term canonicalises either way.
(define (native-bytes bv) (vector 'bytes bv))
(define (native-bytes? x) (bl-tag? x 'bytes))
(define (etf-u32 n acc)
 (cons (bitwise-and n 255) (cons (bitwise-and (arithmetic-shift n -8) 255)
  (cons (bitwise-and (arithmetic-shift n -16) 255) (cons (bitwise-and (arithmetic-shift n -24) 255) acc)))))
(define (etf-u16 n acc) (cons (bitwise-and n 255) (cons (bitwise-and (arithmetic-shift n -8) 255) acc)))
;; Bytes are accumulated in reverse; (etf-bytes list acc) pushes a forward list.
(define (etf-push xs acc) (if (null? xs) acc (etf-push (cdr xs) (cons (car xs) acc))))
(define (etf-atom name acc)
 (let* ((bytes (native-utf8-bytes name)) (n (length bytes)))
  (if (< n 256) (etf-push bytes (cons n (cons 119 acc)))
   (if (< n 65536) (etf-push bytes (etf-u16 n (cons 118 acc))) (native-badarg "atom too long")))))
(define (etf-integer n acc)
 (cond ((and (>= n 0) (< n 256)) (cons n (cons 97 acc)))
  ((and (>= n -2147483648) (< n 2147483648)) (etf-u32 (if (< n 0) (+ n 4294967296) n) (cons 98 acc)))
  (else
   (let digits ((m (abs n)) (out '()))
    (if (> m 0) (digits (arithmetic-shift m -8) (cons (bitwise-and m 255) out))
     (let* ((le (reverse out)) (count (length le)) (sign (if (< n 0) 1 0)))
      (etf-push le (cons sign (if (< count 256) (cons count (cons 110 acc)) (etf-u32 count (cons 111 acc)))))))))))
(define (etf-float f acc)
 (let ((bv (make-bytevector 8 0)))
  (bytevector-ieee-double-set! bv 0 f 'big)
  (etf-push (bytevector->u8-list bv) (cons 70 acc))))
(define (etf-binary bytes acc) (etf-push bytes (etf-u32 (length bytes) (cons 109 acc))))
(define (etf-map-like? x)
 (or (bl-tag? x 'map) (bl-tag? x 'vec) (bl-tag? x 'set) (native-opaque-struct? x)))
(define (etf-encode x acc)
 (cond ((eq? x #t) (etf-atom "true" acc)) ((eq? x #f) (etf-atom "false" acc)) ((bl-is-nil x) (etf-atom "nil" acc))
  ((and (symbol? x) (native-colon-symbol? x)) (etf-atom (native-atom-name x) acc))
  ((and (bl-tag? x 'utf16-keyword) (string? (vector-ref x 1))) (etf-atom (vector-ref x 1) acc))
  ((and (integer? x) (exact? x)) (etf-integer x acc))
  ((bl-tag? x 'float) (etf-float (vector-ref x 1) acc))
  ((string? x) (etf-binary (native-utf8-bytes x) acc))
  ((native-bytes? x) (etf-binary (bytevector->u8-list (vector-ref x 1)) acc))
  ((null? x) (cons 106 acc))
  ((pair? x)
   (let count ((p x) (n 0))
    (if (pair? p) (count (cdr p) (+ n 1))
     (let items ((p x) (acc (etf-u32 n (cons 108 acc))))
      (if (pair? p) (items (cdr p) (etf-encode (car p) acc))
       (if (null? p) (cons 106 acc) (etf-encode p acc)))))))
  ((bl-tag? x 'tuple)
   (let* ((items (bl-items x)) (n (length items)))
    (let loop ((items items) (acc (if (< n 256) (cons n (cons 104 acc)) (etf-u32 n (cons 105 acc)))))
     (if (null? items) acc (loop (cdr items) (etf-encode (car items) acc))))))
  ((etf-map-like? x)
   (let* ((pairs (native-sort (lambda (a b) (native-term-le (bl-nth a 0) (bl-nth b 0)))
                              (native-map-pairs (native-assert-map x)))))
    (let loop ((ps pairs) (acc (etf-u32 (length pairs) (cons 116 acc))))
     (if (null? ps) acc (loop (cdr ps) (etf-encode (bl-nth (car ps) 1) (etf-encode (bl-nth (car ps) 0) acc)))))))
  (else (native-badarg "term_to_binary: no external form for this value"))))
(define (native-term-to-binary x)
 (native-bytes (u8-list->bytevector (reverse (etf-encode x (list 131))))))
(define (etf-options-ok? opts)
 (and (native-list? opts)
  (let loop ((xs opts))
   (or (null? xs)
    (and (or (eq? (car xs) (bl-key "deterministic"))
             (and (bl-tag? (car xs) 'tuple) (= 2 (bl-count (car xs)))
                  (eq? (bl-nth (car xs) 0) (bl-key "minor_version")) (eqv? (bl-nth (car xs) 1) 2)))
         (loop (cdr xs)))))))
(native-add-leaf! "erlang/term_to_binary/1" native-term-to-binary)
(native-add-leaf! "erlang/term_to_binary/2"
 (lambda (x opts) (if (etf-options-ok? opts) (native-term-to-binary x) (native-badarg "term_to_binary option"))))
;; Decoding. Every read checks its bounds; any malformed input is badarg.
(define (etf-bad) (native-raise (bl-key "error") (bl-key "badarg") (native-capture-stack)))
(define (etf-byte bv i) (if (< i (bytevector-length bv)) (bytevector-u8-ref bv i) (etf-bad)))
(define (etf-get-u16 bv i) (+ (* 256 (etf-byte bv i)) (etf-byte bv (+ i 1))))
(define (etf-get-u32 bv i) (+ (* 16777216 (etf-byte bv i)) (* 65536 (etf-byte bv (+ i 1))) (* 256 (etf-byte bv (+ i 2))) (etf-byte bv (+ i 3))))
(define (etf-slice bv i n)
 (if (> (+ i n) (bytevector-length bv)) (etf-bad)
  (let loop ((k (- (+ i n) 1)) (out '())) (if (< k i) out (loop (- k 1) (cons (bytevector-u8-ref bv k) out))))))
(define (etf-utf8-text bytes)
 (with-exception-catcher (lambda (e) #f) (lambda () (native-utf8-string bytes))))
(define (etf-atom-of name)
 (cond ((string=? name "true") #t) ((string=? name "false") #f) ((string=? name "nil") bl-nil) (else (bl-key name))))
(define (etf-latin1 bytes) (list->string (map integer->char bytes)))
(define (etf-struct-value m)
 (let ((mod (native-raw-get m native-struct-key native-missing)))
  (if (or (eq? mod native-vector-module-key) (eq? mod native-set-module-key)) (bl-struct mod m) m)))
;; (value . next-index)
(define (etf-decode bv i)
 (let ((tag (etf-byte bv i)) (i (+ i 1)))
  (case tag
   ((97) (cons (etf-byte bv i) (+ i 1)))
   ((98) (let ((n (etf-get-u32 bv i))) (cons (if (>= n 2147483648) (- n 4294967296) n) (+ i 4))))
   ((70) (let ((bv8 (u8-list->bytevector (etf-slice bv i 8))))
          (cons (bl-float (bytevector-ieee-double-ref bv8 0 'big)) (+ i 8))))
   ((110 111)
    (let* ((count (if (= tag 110) (etf-byte bv i) (etf-get-u32 bv i))) (j (+ i (if (= tag 110) 1 4)))
           (sign (etf-byte bv j)) (digits (etf-slice bv (+ j 1) count))
           (m (let loop ((ds (reverse digits)) (m 0)) (if (null? ds) m (loop (cdr ds) (+ (* m 256) (car ds)))))))
     (cons (if (= sign 0) m (- m)) (+ j 1 count))))
   ((119) (let ((n (etf-byte bv i)))
           (cons (etf-atom-of (or (etf-utf8-text (etf-slice bv (+ i 1) n)) (etf-bad))) (+ i 1 n))))
   ((118) (let ((n (etf-get-u16 bv i)))
           (cons (etf-atom-of (or (etf-utf8-text (etf-slice bv (+ i 2) n)) (etf-bad))) (+ i 2 n))))
   ((115) (let ((n (etf-byte bv i))) (cons (etf-atom-of (etf-latin1 (etf-slice bv (+ i 1) n))) (+ i 1 n))))
   ((100) (let ((n (etf-get-u16 bv i))) (cons (etf-atom-of (etf-latin1 (etf-slice bv (+ i 2) n))) (+ i 2 n))))
   ((106) (cons '() i))
   ((107) (let ((n (etf-get-u16 bv i))) (cons (etf-slice bv (+ i 2) n) (+ i 2 n))))
   ((108)
    (let ((n (etf-get-u32 bv i)))
     (let loop ((k 0) (j (+ i 4)) (out '()))
      (if (< k n) (let ((r (etf-decode bv j))) (loop (+ k 1) (cdr r) (cons (car r) out)))
       (let* ((r (etf-decode bv j)) (tail (car r)))
        (cons (let build ((xs out) (acc tail)) (if (null? xs) acc (build (cdr xs) (cons (car xs) acc)))) (cdr r)))))))
   ((104 105)
    (let ((n (if (= tag 104) (etf-byte bv i) (etf-get-u32 bv i))))
     (let loop ((k 0) (j (+ i (if (= tag 104) 1 4))) (out '()))
      (if (< k n) (let ((r (etf-decode bv j))) (loop (+ k 1) (cdr r) (cons (car r) out)))
       (cons (bl-tuple (reverse out)) j)))))
   ((109)
    (let* ((n (etf-get-u32 bv i)) (bytes (etf-slice bv (+ i 4) n)))
     (cons (or (etf-utf8-text bytes) (native-bytes (u8-list->bytevector bytes))) (+ i 4 n))))
   ((116)
    (let ((n (etf-get-u32 bv i)))
     (let loop ((k 0) (j (+ i 4)) (m (bl-empty-map)))
      (if (< k n)
       (let* ((kr (etf-decode bv j)) (vr (etf-decode bv (cdr kr))))
        (loop (+ k 1) (cdr vr) (native-raw-assoc m (car kr) (car vr))))
       (cons (etf-struct-value m) j)))))
   (else (etf-bad)))))
(define (native-binary-to-term b)
 (let ((bv (cond ((native-bytes? b) (vector-ref b 1))
                 ((string? b) (u8-list->bytevector (native-utf8-bytes b)))
                 (else (etf-bad)))))
  (if (not (eqv? 131 (etf-byte bv 0))) (etf-bad))
  (let ((r (etf-decode bv 1)))
   (if (= (cdr r) (bytevector-length bv)) (car r) (etf-bad)))))
(native-add-leaf! "erlang/binary_to_term/1" native-binary-to-term)
(native-add-leaf! "erlang/binary_to_term/2"
 (lambda (b opts)
  (if (and (native-list? opts) (let ok ((xs opts)) (or (null? xs) (and (eq? (car xs) (bl-key "safe")) (ok (cdr xs))))))
   (native-binary-to-term b) (native-badarg "binary_to_term option"))))
;; Raw file bytes for ETF transport: a byte value in, a byte value out.
(native-add-leaf! "host/read-bytes/1"
 (lambda (path)
  (let* ((port (open-file-input-port path)) (bv (get-bytevector-all port)))
   (close-port port) (native-bytes (if (eof-object? bv) (make-bytevector 0) bv)))))
(native-add-leaf! "host/write-bytes/2"
 (lambda (path b)
  (let ((bv (cond ((native-bytes? b) (vector-ref b 1)) ((string? b) (u8-list->bytevector (native-utf8-bytes b)))
                  (else (native-badarg "bytes expected"))))
        (port (open-file-output-port path (file-options no-fail))))
   (put-bytevector port bv) (close-port port) bl-nil)))
(native-add-leaf! "host/byte-size/1"
 (lambda (b) (if (native-bytes? b) (bytevector-length (vector-ref b 1)) (native-utf8-size b))))
;; A host byte value is a binary to the BL program: is_binary/is_bitstring
;; answer true (the emitted intrinsic agrees) and byte_size counts its bytes.
;; Text operations still take only strings.
(let ((text-binary? (native-leaf "erlang/is_binary/1")) (text-size (native-leaf "erlang/byte_size/1")))
 (native-replace-leaf! "erlang/is_binary/1" (lambda (x) (or (native-bytes? x) (text-binary? x))))
 (native-replace-leaf! "erlang/is_bitstring/1" (lambda (x) (or (native-bytes? x) (text-binary? x))))
 (native-replace-leaf! "erlang/byte_size/1"
  (lambda (x) (if (native-bytes? x) (bytevector-length (vector-ref x 1)) (text-size x)))))
