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
(define (etf-byte-list? p n)
 (cond ((null? p) (> n 0)) ((not (pair? p)) #f) ((>= n 65535) #f)
  ((let ((x (car p))) (and (integer? x) (exact? x) (>= x 0) (< x 256))) (etf-byte-list? (cdr p) (+ n 1)))
  (else #f)))
(define (etf-encode x acc)
 (cond ((eq? x #t) (etf-atom "true" acc)) ((eq? x #f) (etf-atom "false" acc)) ((bl-is-nil x) (etf-atom "nil" acc))
  ((and (symbol? x) (native-colon-symbol? x)) (etf-atom (native-atom-name x) acc))
  ((and (bl-tag? x 'utf16-keyword) (string? (vector-ref x 1))) (etf-atom (vector-ref x 1) acc))
  ((and (integer? x) (exact? x)) (etf-integer x acc))
  ((bl-tag? x 'float) (etf-float (vector-ref x 1) acc))
  ((string? x) (etf-binary (native-utf8-bytes x) acc))
  ((native-bytes? x) (etf-binary (bytevector->u8-list (vector-ref x 1)) acc))
  ((null? x) (cons 106 acc))
  ;; STRING_EXT, as the BEAM writes a proper list of 1..65535 bytes.
  ((and (pair? x) (etf-byte-list? x 0)) (etf-push x (etf-u16 (length x) (cons 107 acc))))
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
  ;; erlang:external_size/1 only measures: a closure or reference counts as a
  ;; fixed-size stand-in (the BEAM's own sizes depend on its code and node).
  (etf-measuring? (etf-push (make-list 32 0) acc))
  (else (native-badarg "term_to_binary: no external form for this value"))))
(define etf-measuring? #f)
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

;; ── Front end: the Elixir stdlib and Env tables priv/host/aot.bl stages with ─
;; Only keys no earlier host file provides are added here; the service
;; refusals (native-refusals.scm) load last and skip any key provided here.
(define (nf-leaf! key proc) (if (not (native-map-has? native-leaf-registry key)) (native-add-leaf! key proc)))
(define (nf-key-error key m)
 (native-raise (bl-key "error")
  (native-exception-struct "Elixir.KeyError" (native-nil-defaults '("key" "term" "message"))
   (list (bl-make-tuple (bl-key "key") key) (bl-make-tuple (bl-key "term") m)))
  (native-capture-stack)))
(define (nf-has? m k) (native-raw-map-has? m k))
(define (nf-get m k d) (native-raw-map-get m k d))
(nf-leaf! "Elixir.Map/new/0" (lambda () (bl-empty-map)))
(nf-leaf! "Elixir.Map/put/3" (lambda (m k v) (native-raw-map-put k v m)))
(nf-leaf! "Elixir.Map/has_key?/2" nf-has?)
(nf-leaf! "Elixir.Map/keys/1" (lambda (m) (native-map-keys (native-assert-map m))))
(nf-leaf! "Elixir.Map/values/1" (lambda (m) (map (lambda (p) (bl-nth p 1)) (native-map-pairs (native-assert-map m)))))
(nf-leaf! "Elixir.Map/merge/2" native-map-merge)
(nf-leaf! "Elixir.Map/put_new/3" (lambda (m k v) (if (nf-has? m k) m (native-raw-map-put k v m))))
(nf-leaf! "Elixir.Map/fetch!/2" (lambda (m k) (let ((v (nf-get m k native-missing))) (if (eq? v native-missing) (nf-key-error k m) v))))
(nf-leaf! "Elixir.Map/fetch/2"
 (lambda (m k) (let ((v (nf-get m k native-missing))) (if (eq? v native-missing) (bl-key "error") (bl-make-tuple (bl-key "ok") v)))))
(nf-leaf! "Elixir.Map/take/2"
 (lambda (m keys) (let loop ((ks (native-finite-items keys)) (out (bl-empty-map)))
  (if (null? ks) out (loop (cdr ks) (let ((v (nf-get m (car ks) native-missing))) (if (eq? v native-missing) out (native-raw-assoc out (car ks) v))))))))
(nf-leaf! "Elixir.Map/update!/3"
 (lambda (m k f) (let ((v (nf-get m k native-missing))) (if (eq? v native-missing) (nf-key-error k m) (native-raw-map-put k (bl-invoke f (list v)) m)))))
;; Elixir MapSet: %MapSet{map: %{member => []}}, as on the BEAM. to_list is
;; the inner map's key order (term order for the small sets staging builds).
(define nf-mapset-key (bl-key "Elixir.MapSet"))
(define (nf-mapset inner) (bl-map (bl-key "__struct__") nf-mapset-key (bl-key "map") inner))
(define (nf-mapset-inner s)
 (if (and (bl-tag? s 'map) (eq? (nf-get s native-struct-key bl-nil) nf-mapset-key)) (nf-get s (bl-key "map") (bl-empty-map))
  (native-badarg "MapSet expected")))
(define (nf-mapset-from xs) (let loop ((xs xs) (m (bl-empty-map))) (if (null? xs) (nf-mapset m) (loop (cdr xs) (native-raw-assoc m (car xs) '())))))
(define (nf-mapset-keys s) (native-sort native-term-le (native-map-keys (nf-mapset-inner s))))
(nf-leaf! "Elixir.MapSet/new/0" (lambda () (nf-mapset (bl-empty-map))))
(nf-leaf! "Elixir.MapSet/new/1" (lambda (xs) (if (and (bl-tag? xs 'map) (eq? (nf-get xs native-struct-key bl-nil) nf-mapset-key)) xs (nf-mapset-from (native-finite-items xs)))))
(nf-leaf! "Elixir.MapSet/new/2" (lambda (xs f) (nf-mapset-from (map (lambda (x) (bl-invoke f (list x))) (native-finite-items xs)))))
(nf-leaf! "Elixir.MapSet/put/2" (lambda (s x) (nf-mapset (native-raw-assoc (nf-mapset-inner s) x '()))))
(nf-leaf! "Elixir.MapSet/member?/2" (lambda (s x) (nf-has? (nf-mapset-inner s) x)))
(nf-leaf! "Elixir.MapSet/to_list/1" nf-mapset-keys)
(nf-leaf! "Elixir.MapSet/size/1" (lambda (s) (native-map-count (nf-mapset-inner s))))
(nf-leaf! "Elixir.MapSet/union/2" (lambda (a b) (nf-mapset (native-map-merge (nf-mapset-inner a) (nf-mapset-inner b)))))
(nf-leaf! "Elixir.MapSet/difference/2"
 (lambda (a b) (let ((drop (nf-mapset-inner b)))
  (nf-mapset (let loop ((ks (native-map-keys (nf-mapset-inner a))) (m (nf-mapset-inner a)))
   (if (null? ks) m (loop (cdr ks) (if (nf-has? drop (car ks)) (native-raw-remove m (car ks)) m))))))))
;; Enum over finite collections; callbacks answer BL truthiness.
(define (nf-true? f x) (bl-truthy (bl-invoke f (list x))))
(nf-leaf! "Elixir.Enum/member?/2"
 (lambda (xs x) (if (and (bl-tag? xs 'map) (eq? (nf-get xs native-struct-key bl-nil) nf-mapset-key)) (nf-has? (nf-mapset-inner xs) x)
  (let loop ((ys (native-finite-items xs))) (cond ((null? ys) #f) ((bl-key-equal? (car ys) x) #t) (else (loop (cdr ys))))))))
(nf-leaf! "Elixir.Enum/any?/2" (lambda (xs f) (let loop ((ys (native-finite-items xs))) (cond ((null? ys) #f) ((nf-true? f (car ys)) #t) (else (loop (cdr ys)))))))
(nf-leaf! "Elixir.Enum/find/2" (lambda (xs f) (let loop ((ys (native-finite-items xs))) (cond ((null? ys) bl-nil) ((nf-true? f (car ys)) (car ys)) (else (loop (cdr ys)))))))
(nf-leaf! "Elixir.Enum/find_value/2"
 (lambda (xs f) (let loop ((ys (native-finite-items xs))) (if (null? ys) bl-nil (let ((v (bl-invoke f (list (car ys))))) (if (bl-truthy v) v (loop (cdr ys))))))))
(nf-leaf! "Elixir.Enum/reject/2" (lambda (xs f) (let loop ((ys (native-finite-items xs)) (out '())) (if (null? ys) (reverse out) (loop (cdr ys) (if (nf-true? f (car ys)) out (cons (car ys) out)))))))
(nf-leaf! "Elixir.Enum/count/1" (lambda (xs) (length (native-finite-items xs))))
(nf-leaf! "Elixir.Enum/at/2"
 (lambda (xs i) (let* ((ys (native-finite-items xs)) (n (length ys)) (j (if (< i 0) (+ n i) i)))
  (if (and (>= j 0) (< j n)) (list-ref ys j) bl-nil))))
(nf-leaf! "Elixir.Enum/split_with/2"
 (lambda (xs f) (let loop ((ys (native-finite-items xs)) (a '()) (b '()))
  (if (null? ys) (bl-make-tuple (reverse a) (reverse b))
   (if (nf-true? f (car ys)) (loop (cdr ys) (cons (car ys) a) b) (loop (cdr ys) a (cons (car ys) b)))))))
(nf-leaf! "Elixir.Enum/sort/2"
 (lambda (xs how)
  (let ((ys (native-finite-items xs)))
   (cond ((eq? how (bl-key "asc")) (native-sort native-term-le ys))
    ((eq? how (bl-key "desc")) (native-sort (lambda (a b) (native-term-le b a)) ys))
    (else (native-sort (lambda (a b) (bl-truthy (bl-invoke how (list a b)))) ys))))))
(nf-leaf! "Elixir.Enum/group_by/3"
 (lambda (xs kf vf)
  (let loop ((ys (reverse (native-finite-items xs))) (m (bl-empty-map)))
   (if (null? ys) m
    (let ((k (bl-invoke kf (list (car ys)))) (v (bl-invoke vf (list (car ys)))))
     (loop (cdr ys) (native-raw-assoc m k (cons v (nf-get m k '())))))))))
(nf-leaf! "Elixir.Enum/uniq_by/2"
 (lambda (xs f) (let loop ((ys (native-finite-items xs)) (seen (bl-empty-map)) (out '()))
  (if (null? ys) (reverse out)
   (let ((k (bl-invoke f (list (car ys)))))
    (if (nf-has? seen k) (loop (cdr ys) seen out) (loop (cdr ys) (native-raw-assoc seen k #t) (cons (car ys) out))))))))
(nf-leaf! "Elixir.Keyword/put_new/3"
 (lambda (kw k v) (if (native-keyword-find kw k) kw (cons (bl-make-tuple k v) kw))))
(nf-leaf! "Elixir.List/wrap/1" (lambda (x) (cond ((bl-is-nil x) '()) ((or (null? x) (pair? x)) x) (else (list x)))))
(nf-leaf! "Elixir.List/to_tuple/1" (lambda (xs) (bl-tuple (native-assert-list xs))))
(nf-leaf! "Elixir.List/last/1" (lambda (xs) (if (null? xs) bl-nil (car (last-pair xs)))))
(nf-leaf! "Elixir.List/keyfind/3"
 (lambda (xs key pos) (let loop ((ys xs))
  (cond ((null? ys) bl-nil)
   ((and (bl-tag? (car ys) 'tuple) (> (bl-count (car ys)) pos) (bl-key-equal? (bl-nth (car ys) pos) key)) (car ys))
   (else (loop (cdr ys)))))))
(nf-leaf! "Elixir.Process/delete/1"
 (lambda (k) (let ((old (native-pdict-erase k))) (if (eq? old (bl-key "undefined")) bl-nil old))))
(nf-leaf! "Elixir.String/to_existing_atom/1" bl-key)
;; Env namespace definition tables (Env.put_ns_definition and friends): one
;; map per namespace in the native Env rows, the shape the BEAM's ETS holds.
(define (nf-defs-row ns) (native-row (bl-key "ns_defs") ns))
(define (nf-ns-defs ns) (let ((v (native-env-value (nf-defs-row ns)))) (if (eq? v native-missing) (bl-empty-map) v)))
(nf-leaf! "Elixir.BeamLisp.Env/ns_defs/1" nf-ns-defs)
(nf-leaf! "Elixir.BeamLisp.Env/put_ns_defs/2" (lambda (ns defs) (native-env-put! (nf-defs-row ns) defs) (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.Env/put_ns_definition/3"
 (lambda (ns name entries) (native-env-put! (nf-defs-row ns) (native-raw-assoc (nf-ns-defs ns) name entries)) (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.Env/selected_ns_definitions/2"
 (lambda (ns names) (let ((defs (nf-ns-defs ns)))
  (let loop ((ns names) (out (bl-empty-map)))
   (if (null? ns) out (loop (cdr ns) (let ((v (nf-get defs (car ns) native-missing))) (if (eq? v native-missing) out (native-raw-assoc out (car ns) v)))))))))

;; ── Front end: the custody world and the staging path's leaves ─────────────
;; The native front end runs priv/host/aot.bl's staging and description code
;; on one SDK whose custody facts the BEAM computed once (front-end/custody.bl).
;; host/nf-install-world/1 installs them; the leaves below answer from them.
;; Env fork/bind/capture are exact snapshots of this image's Env rows: there is
;; one process and one row table, so a fork saves the rows and destroy puts
;; them back (the rows a view wrote die with it, as on the BEAM). The process
;; dictionary is not part of an env.
(define nf-world (make-parameter #f))
(define nf-locks (make-parameter '()))
(define (nf-world-get k . d)
 (let ((w (nf-world))) (if (and w (native-raw-map-has? w k)) (native-raw-map-get w k (if (null? d) bl-nil (car d)))
  (if (null? d) bl-nil (car d)))))
(define (nf-call thunk) (if (procedure? thunk) (bl-invoke thunk '()) thunk))
(define (native-char-data* x) (if (string? x) x (native-atom-name x)))
(nf-leaf! "host/nf-world-key/0" (lambda () (nf-world-get (bl-key "compiler-key") "")))
(nf-leaf! "host/nf-install-world/1"
 (lambda (w) (nf-world w) (set! native-env-search-paths '()) (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.Tiers/priv_root/0" (lambda () (nf-world-get (bl-key "priv-root"))))
(nf-leaf! "Elixir.BeamLisp.Tiers/library_names/0" (lambda () (nf-world-get (bl-key "library-names") '())))
(nf-leaf! "Elixir.BeamLisp.Tiers/build_namespaces/0" (lambda () (nf-world-get (bl-key "build-namespaces") '())))
(define (nf-string-prefix? p s)
 (and (>= (string-length s) (string-length p)) (string=? (substring s 0 (string-length p)) p)))
(nf-leaf! "Elixir.BeamLisp.Tiers/boot_source?/1"
 (lambda (file) (let ((f (if (string? file) file (native-atom-name file))))
  (nf-string-prefix? (string-append (nf-world-get (bl-key "priv-root") "") "/boot/") f))))
(nf-leaf! "Elixir.BeamLisp.Tiers/tier_of_ns/1" (lambda (ns) (bl-key "library")))
(nf-leaf! "Elixir.BeamLisp.Tiers/dirs/0" (lambda () (list (nf-world-get (bl-key "priv-root")))))
;; Loader: source text and paths come from the world's namespace table.
(define (nf-ns-entry ns) (native-raw-map-get (nf-world-get (bl-key "namespaces") (bl-empty-map)) ns native-missing))
(nf-leaf! "Elixir.BeamLisp.Loader/read_source/1" (lambda (path) (native-read-file path)))
(nf-leaf! "Elixir.BeamLisp.Loader/declared_ns/1"
 (lambda (text)
  (let* ((n (string-length text))
         (stop-at (lambda (c) (or (char=? c #\space) (char=? c #\)) (char=? c #\newline) (char=? c #\tab)))))
   (let find ((i 0))
    (cond ((>= i (- n 4)) (native-badarg "no ns form"))
     ((and (char=? (string-ref text i) #\() (char=? (string-ref text (+ i 1)) #\n)
           (char=? (string-ref text (+ i 2)) #\s) (char=? (string-ref text (+ i 3)) #\space))
      (let scan ((k (+ i 4)))
       (cond ((>= k n) (native-badarg "no ns name"))
        ((char=? (string-ref text k) #\space) (scan (+ k 1)))
        ((char=? (string-ref text k) #\() (native-badarg "no ns name"))
        (else (let end ((m k))
                (if (or (>= m n) (char=? (string-ref text m) #\space) (char=? (string-ref text m) #\))
                        (char=? (string-ref text m) #\newline) (char=? (string-ref text m) #\tab))
                 (substring text k m)
                 (end (+ m 1))))))))
     (else (find (+ i 1))))))))
(nf-leaf! "Elixir.BeamLisp.Loader/source_path/1"
 (lambda (ns) (let ((e (nf-ns-entry ns))) (if (eq? e native-missing) bl-nil (native-raw-map-get e (bl-key "file") bl-nil)))))
(nf-leaf! "Elixir.BeamLisp.Loader/with_load_path/2" (lambda (path thunk) (nf-call thunk)))
(nf-leaf! "Elixir.BeamLisp.Loader/without_initialization/1" (lambda (thunk) (nf-call thunk)))
(nf-leaf! "Elixir.BeamLisp.Loader/search_dirs/0" (lambda () (list (nf-world-get (bl-key "priv-root")))))
(nf-leaf! "Elixir.BeamLisp.Loader/find_file/1"
 (lambda (ns) (let ((e (nf-ns-entry ns))) (if (eq? e native-missing) bl-nil (native-raw-map-get e (bl-key "file") bl-nil)))))
(nf-leaf! "Elixir.BeamLisp.Loader/source_decls/1" (lambda (ns) (bl-empty-map)))
(nf-leaf! "Elixir.BeamLisp.Loader/source_decls_from/2" (lambda (ns text) (bl-empty-map)))
(nf-leaf! "Elixir.BeamLisp.Loader/assert_initializer_execution_allowed!/1" (lambda (ns) (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.Loader/ensure_ready/1" (lambda (ns) (bl-key "ok")))
;; AOTCache: one SDK, its compiler key fixed at custody time.
(nf-leaf! "Elixir.BeamLisp.AOTCache/compiler_key/0" (lambda () (nf-world-get (bl-key "compiler-key") "")))
(nf-leaf! "Elixir.BeamLisp.AOTCache/current_compiler_key/0" (lambda () (nf-world-get (bl-key "compiler-key") "")))
(nf-leaf! "Elixir.BeamLisp.AOTCache/enabled?/0" (lambda () #f))
(nf-leaf! "Elixir.BeamLisp.AOTCache/key_for_ns/1"
 (lambda (ns) (native-raw-map-get (nf-world-get (bl-key "keys") (bl-empty-map)) ns "")))
(nf-leaf! "Elixir.BeamLisp.AOTCache/key_for_source/1"
 (lambda (path) (let loop ((rows (nf-world-get (bl-key "namespaces") (bl-empty-map))))
  (if (not (bl-tag? rows 'map)) "" (let ((e (native-map-pairs rows)))
   (let scan ((ps e)) (cond ((null? ps) "")
    ((string=? (native-raw-map-get (bl-nth (car ps) 1) (bl-key "file") "") path)
     (native-raw-map-get (nf-world-get (bl-key "source-hashes") (bl-empty-map)) (bl-nth (car ps) 0) ""))
    (else (scan (cdr ps))))))))))
;; Env custody: exact row snapshots.
(define nf-env-stack '())
;; Put a saved row map back: rebuild the exact-key index from it and republish
;; every (ns name) row whose value changed, as native-env-put! does per row.
(define (nf-restore-rows! rows)
 (let ((before native-env-rows))
  (if (not (eq? before rows))
   (let ((old (make-table test: equal?)) (changed '()))
    (for-each (lambda (p) (table-set! old (bl-nth p 0) (bl-nth p 1))) (native-map-pairs before))
    (set! native-env-rows rows)
    (set! native-env-index (make-table test: equal?))
    (set! native-env-index-exact? #t)
    (for-each (lambda (p)
               (let ((k (bl-nth p 0)) (v (bl-nth p 1)))
                (if (native-env-index-key? k) (table-set! native-env-index k v) (set! native-env-index-exact? #f))
                (if (not (eq? (table-ref old k native-missing) v)) (set! changed (cons k changed)))
                (table-set! old k native-missing)))
     (native-map-pairs rows))
    (table-for-each (lambda (k v) (if (not (eq? v native-missing)) (set! changed (cons k changed)))) old)
    (for-each (lambda (k) (if (not (native-sealed-row? k)) (native-env-row-changed! k))) changed)
    (native-link-changed!)))))
(nf-leaf! "Elixir.BeamLisp.Env/capture/0"
 (lambda () (bl-map (bl-key "rows") native-env-rows (bl-key "ns") native-env-current
                     (bl-key "pdict") (native-pdict))))
(nf-leaf! "Elixir.BeamLisp.Env/bind/1"
 (lambda (snapshot)
  (nf-restore-rows! (bl-get snapshot (bl-key "rows") native-env-rows))
  (set! native-env-current (bl-get snapshot (bl-key "ns") native-env-current))
  (if (native-map-has? snapshot (bl-key "pdict")) (native-pdict (bl-get snapshot (bl-key "pdict"))))
  (native-link-changed!) (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.Env/fork/1"
 (lambda (how)
  (let ((token (native-unique-integer)))
   (set! nf-env-stack (cons (list token native-env-rows native-env-current) nf-env-stack))
   token)))
(nf-leaf! "Elixir.BeamLisp.Env/destroy/1"
 (lambda (token)
  (let scan ((rest nf-env-stack))
   (cond ((null? rest) bl-nil)
    ((eqv? (car (car rest)) token)
     (nf-restore-rows! (cadr (car rest))) (set! native-env-current (caddr (car rest)))
     (set! nf-env-stack (cdr rest)) (native-link-changed!) (bl-key "ok"))
    (else (scan (cdr rest)))))))
;; with_env binds the env id the thunk sees (env_id/0), as the BEAM's
;; process dictionary does; the rows themselves are the one native table.
(define nf-env-current #f)
(define (nf-set-leaf! key proc) (if (native-map-has? native-leaf-registry key) (native-replace-leaf! key proc) (native-add-leaf! key proc)))
(nf-leaf! "Elixir.BeamLisp.Env/with_env/2"
 (lambda (token thunk)
  (let ((saved nf-env-current))
   (dynamic-wind (lambda () (set! nf-env-current token) (set! native-env-view-active? (not (eq? token (bl-key "global")))))
                 (lambda () (nf-call thunk))
                 (lambda () (set! nf-env-current saved) (set! native-env-view-active? (and saved (not (eq? saved (bl-key "global"))) #t)))))))
(nf-leaf! "Elixir.BeamLisp.Env/with_namespace_lock/2" (lambda (ns thunk) (nf-call thunk)))
(nf-leaf! "Elixir.BeamLisp.Env/with_publication/2" (lambda (ns thunk) (nf-call thunk)))
(nf-leaf! "Elixir.BeamLisp.Env/with_module_locks/2" (lambda (mods thunk) (nf-call thunk)))
(nf-leaf! "Elixir.BeamLisp.Env/with_code_evidence_publication/1" (lambda (thunk) (nf-call thunk)))
(nf-leaf! "Elixir.BeamLisp.Env/code_evidence_generation/0" (lambda () 0))
(nf-leaf! "Elixir.BeamLisp.Env/live_toolchain_keys/0" (lambda () (list (nf-world-get (bl-key "compiler-key") ""))))
(nf-leaf! "Elixir.BeamLisp.Env/current_ns/0" (lambda () native-env-current))
(nf-leaf! "Elixir.BeamLisp.Env/in_ns/1" (lambda (ns) (set! native-env-current ns) (native-declare-ns ns) ns))
(define native-env-search-paths '())
(nf-leaf! "Elixir.BeamLisp.Env/add_search_path/1" (lambda (p) (set! native-env-search-paths (cons p native-env-search-paths)) (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.Env/local_var?/2"
 (lambda (ns name) (not (eq? (native-env-value (native-row (bl-key "ns_defs") ns)) native-missing))))
(nf-leaf! "Elixir.BeamLisp.Env/ns_definition/2" (lambda (ns name) (native-raw-map-get (nf-ns-defs ns) name nil)))
(nf-leaf! "Elixir.BeamLisp.Env/candidates/2" (lambda (ns name) (native-candidates ns name)))
(nf-leaf! "Elixir.BeamLisp.Env/put_link/3" (lambda (ns name link) (native-env-put! (native-row (bl-key "link") ns name) link) (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.Env/match/1" (lambda (pattern) (native-match-rows pattern)))
(define (native-match-rows pattern)
 (let ((kind (bl-nth pattern 0)))
  (let loop ((ps (native-map-pairs native-env-rows)) (out '()))
   (if (null? ps) (reverse out)
    (let* ((p (car ps)) (key (bl-nth p 0)))
     (if (and (bl-tag? key 'tuple) (>= (bl-count key) 2) (eq? (bl-nth key 0) (bl-nth kind 1)))
      (loop (cdr ps) (cons (bl-tuple (append (bl-items key) (list (bl-nth p 1)))) out))
      (loop (cdr ps) out)))))))
;; Bootstrap and package authority: metadata the descriptor asks for; the
;; native front end computes descriptors only and publishes nothing.
(nf-leaf! "Elixir.BeamLisp.Bootstrap/manifest/0" (lambda () bl-nil))
(nf-leaf! "Elixir.BeamLisp.Bootstrap/seed_dir/0" (lambda () bl-nil))
(nf-leaf! "Elixir.BeamLisp.Bootstrap/loaded_claimed?/0" (lambda () #f))
(nf-leaf! "Elixir.BeamLisp.Bootstrap/packaged_member?/1" (lambda (f) #f))
(nf-leaf! "Elixir.BeamLisp.Bootstrap/key_matches?/2" (lambda (a b) #f))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/sdk_unit_compiled?/2" (lambda (ns key) #t))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/sdk_compiler_row/1" (lambda (ns) bl-nil))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/sdk_unit_evidence/2" (lambda (ns key) bl-nil))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/factory_lambda_origins!/1" (lambda (x) bl-nil))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/kernel_callback_origins!/1" (lambda (x) bl-nil))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/local_package_authority/1" (lambda (x) bl-nil))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/local_package_authority_report/0" (lambda () bl-nil))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/runtime_sdk_entries!/1" (lambda (x) bl-nil))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/sdk_checked_declaration_table/1" (lambda (ns) (bl-empty-map)))
;; Small stdlib leaves the staging path uses.
(nf-leaf! "Elixir.Kernel/struct/2" (lambda (mod fields) (bl-struct mod fields)))
(nf-leaf! "Elixir.Map/from_struct/1" (lambda (m) (native-raw-remove m native-struct-key)))
(nf-leaf! "Elixir.Map/drop/2"
 (lambda (m keys) (let loop ((ks (native-finite-items keys)) (out m))
  (if (null? ks) out (loop (cdr ks) (native-raw-remove out (car ks)))))))
(define (nf-keyword-drop kw key)
 (let loop ((xs kw)) (cond ((not (pair? xs)) '()) ((bl-key-equal? (bl-nth (car xs) 0) key) (cdr xs)) (else (cons (car xs) (loop (cdr xs)))))))
(nf-leaf! "Elixir.Keyword/put/3" (lambda (kw k v) (cons (bl-make-tuple k v) (nf-keyword-drop kw k))))
(nf-leaf! "Elixir.Keyword/take/2"
 (lambda (kw keys) (let loop ((ks (native-finite-items keys)) (out '()))
  (if (null? ks) (reverse out) (loop (cdr ks) (let ((p (native-keyword-find kw (car ks)))) (if p (cons p out) out)))))))
(nf-leaf! "Elixir.Keyword/get/3"
 (lambda (kw k d) (let ((p (native-keyword-find kw k))) (if p (bl-nth p 1) d))))
(nf-leaf! "Elixir.Keyword/fetch!/2"
 (lambda (kw k) (let ((p (native-keyword-find kw k))) (if p (bl-nth p 1) (nf-key-error k kw)))))
(nf-leaf! "Elixir.List/to_string/1"
 (lambda (xs) (let loop ((cs (native-finite-items xs)) (out ""))
  (if (null? cs) out (loop (cdr cs) (string-append out (native-atom-name (car cs))))))))
;; Elixir Range.new/2: first..last with step -1 when first > last (the
;; deprecated implicit decreasing range, which 0..-1 still is).
(nf-leaf! "Elixir.Range/new/2"
 (lambda (a b) (bl-struct "Elixir.Range" (bl-map (bl-key "first") a (bl-key "last") b (bl-key "step") (if (<= a b) 1 -1)))))
(define nf-range-key (bl-key "Elixir.Range"))
(define (nf-range? x) (and (bl-tag? x 'map) (eq? (native-raw-map-get x native-struct-key bl-nil) nf-range-key)))
(define (nf-range-items r)
 (let ((first (native-raw-map-get r (bl-key "first") 0)) (last (native-raw-map-get r (bl-key "last") 0))
       (step (native-raw-map-get r (bl-key "step") 1)))
  (let loop ((i first) (out '()))
   (if (if (> step 0) (> i last) (< i last)) (reverse out) (loop (+ i step) (cons i out))))))
(nf-leaf! "Elixir.Macro/camelize/1"
 (lambda (s) (let loop ((cs (string->list (native-char-data s))) (out '()) (up #t))
  (if (null? cs) (list->string (reverse out))
   (let ((c (car cs)))
    (if (char=? c #\_) (loop (cdr cs) out #t)
     (loop (cdr cs) (cons (if up (char-upcase c) c) out) #f)))))))
(nf-leaf! "Elixir.Module/concat/1" (lambda (xs) (apply string-append (map native-char-data* (native-finite-items xs)))))
(nf-leaf! "Elixir.IO/puts/1" (lambda (x) (display (native-char-data* x)) (newline) (bl-key "ok")))
(nf-leaf! "Elixir.Process/whereis/1" (lambda (name) (bl-key "undefined")))
(nf-leaf! "Elixir.Code/ensure_loaded?/1" (lambda (mod) (erlang-module-loaded? mod)))
(define (erlang-module-loaded? mod)
 (or (not (eq? (bl-get native-module-names (native-module-name mod) native-missing) native-missing))
     (not (eq? (native-env-value (native-row (bl-key "ns") (native-module-name mod))) native-missing))))
(nf-leaf! "application/get_application/1" (lambda (app) (bl-key "undefined")))
(nf-leaf! "Elixir.System/get_env/1" (lambda (k) (let ((v (getenv (native-char-data k)))) (if v v bl-nil))))
(nf-leaf! "Elixir.System/version/0" (lambda () "28"))

;; The pinned Reader host module (priv/host/reader.bl) is not in this image;
;; its two services are the compiled `reader` namespace plus a no-op atom
;; guard (the native reader interns into an already-fixed atom table).
(define (nf-reader-read-string source path) (bl-invoke (native-global-exact "reader" "read-string") (list source path)))
(nf-leaf! "Elixir.BeamLisp.Reader/read_string/2" nf-reader-read-string)
(nf-leaf! "Elixir.BeamLisp.Reader/read_string/1" (lambda (source) (nf-reader-read-string source "native-front")))
(nf-leaf! "Elixir.BeamLisp.Reader/read_first/1" (lambda (source) (let ((fs (nf-reader-read-string source "native-front"))) (if (null? fs) bl-nil (car fs)))))
(nf-leaf! "Elixir.BeamLisp.Reader/read_all/1" (lambda (source) (nf-reader-read-string source "native-front")))
(nf-leaf! "Elixir.BeamLisp.Reader/mapping_atom_limit/1" (lambda (thunk) (nf-call thunk)))
(nf-leaf! "Elixir.BeamLisp.AtomGuard/reset/0" (lambda () (bl-key "ok")))
(nf-leaf! "Elixir.BeamLisp.AtomGuard/account!/1" (lambda (n) (bl-key "ok")))

;; ── Front end: files, paths, strings, tuples (staging reads source trees) ──
(define (native-path-join a b)
 (cond ((string=? a "") b) ((string=? b "") a)
  ((char=? (string-ref a (- (string-length a) 1)) #\/) (string-append a b))
  (else (string-append a "/" b))))
(define (nf-file-size path) (let* ((p (open-file-input-port path)) (n (port-length p))) (close-port p) n))
(define (nf-stat-file path)
 (if (not (file-exists? path)) (bl-key "error")
  (bl-map (bl-key "__struct__") (bl-key "Elixir.File.Stat")
          (bl-key "size") (if (file-directory? path) 4096 (nf-file-size path))
          (bl-key "type") (if (file-directory? path) (bl-key "directory")
                           (if (file-regular? path) (bl-key "regular") (bl-key "other")))
          (bl-key "mode") 0 (bl-key "mtime") bl-nil (bl-key "atime") bl-nil (bl-key "ctime") bl-nil
          (bl-key "inode") 0 (bl-key "major_device") 0 (bl-key "minor_device") 0
          (bl-key "links") 1 (bl-key "uid") 0 (bl-key "gid") 0)))
(nf-leaf! "Elixir.File/stat/1"
 (lambda (path) (let ((s (nf-stat-file path))) (if (eq? s (bl-key "error")) (bl-make-tuple (bl-key "error") (bl-key "enoent"))
  (bl-make-tuple (bl-key "ok") s)))))
(nf-leaf! "Elixir.File/stat!/1"
 (lambda (path) (let ((s (nf-stat-file path))) (if (eq? s (bl-key "error"))
  (native-raise (bl-key "error") (native-exception-struct "Elixir.File.Error" (native-nil-defaults '("reason" "path" "action" "message"))
                  (list (bl-make-tuple (bl-key "reason") (bl-key "enoent")) (bl-make-tuple (bl-key "path") path))) (native-capture-stack))
  s))))
(nf-leaf! "Elixir.File/exists?/1" (lambda (p) (file-exists? p)))
(nf-leaf! "Elixir.File/regular?/1" (lambda (p) (and (file-exists? p) (file-regular? p))))
(nf-leaf! "Elixir.File/dir?/1" (lambda (p) (and (file-exists? p) (file-directory? p))))
(nf-leaf! "Elixir.File/read!/1" (lambda (p) (native-read-file p)))
(nf-leaf! "Elixir.File/read_link/1" (lambda (p) (let ((t (with-exception-catcher (lambda (e) #f) (lambda () (read-link p))))) (if t (bl-make-tuple (bl-key "ok") t) (bl-make-tuple (bl-key "error") (bl-key "enoent"))))))
(nf-leaf! "Elixir.File/ls!/1" (lambda (p) (map (lambda (n) (if (native-colon-symbol? n) n n)) (directory-list p))))
(nf-leaf! "Elixir.File/cwd!/0" (lambda () (current-directory)))
(nf-leaf! "Elixir.File/mkdir_p!/1" (lambda (p) (with-exception-catcher (lambda (e) e) (lambda () (if (not (file-directory? p)) (mkdir p)))) (bl-key "ok")))
(nf-leaf! "Elixir.Path/join/2" (lambda (a b) (native-path-join a b)))
(nf-leaf! "Elixir.Path/dirname/1"
 (lambda (p) (let loop ((i (- (string-length p) 1)))
  (cond ((< i 0) ".") ((char=? (string-ref p i) #\/) (if (= i 0) "/" (substring p 0 i))) (else (loop (- i 1)))))))
(nf-leaf! "Elixir.Path/basename/1"
 (lambda (p) (let loop ((i (- (string-length p) 1)))
  (cond ((< i 0) p) ((char=? (string-ref p i) #\/) (substring p (+ i 1) (string-length p))) (else (loop (- i 1)))))))
(nf-leaf! "Elixir.Path/expand/1" (lambda (p) (if (and (> (string-length p) 0) (char=? (string-ref p 0) #\/)) p (native-path-join (current-directory) p))))
(nf-leaf! "Elixir.Path/split/1"
 (lambda (p) (let* ((n (string-length p)) (i (let loop ((i (- n 1))) (cond ((< i 0) #f) ((char=? (string-ref p i) #\/) i) (else (loop (- i 1)))))))
  (bl-make-tuple (if i (if (= i 0) "/" (substring p 0 i)) ".") (if i (substring p (+ i 1) n) p)))))
(nf-leaf! "Elixir.Path/type/1" (lambda (p) (if (file-directory? p) (bl-key "directory") (if (file-regular? p) (bl-key "regular") (bl-key "other")))))
(nf-leaf! "Elixir.Path/relative_to/2"
 (lambda (p base) (let ((b (if (and (> (string-length base) 0) (char=? (string-ref base (- (string-length base) 1)) #\/)) base (string-append base "/"))))
  (if (nf-string-prefix? b p) (substring p (string-length b) (string-length p)) p))))
(nf-leaf! "Elixir.Path/wildcard/2" (lambda (pattern opts) (list)))
(nf-leaf! "Elixir.System/unique_integer/1" (lambda (opts) (native-unique-integer)))
(nf-leaf! "Elixir.Tuple/insert_at/3"
 (lambda (t i v) (native-assert-tuple t)
  (bl-tuple (let loop ((xs (bl-items t)) (k 0) (out '()))
             (cond ((null? xs) (if (<= i k) (reverse (cons v out)) (reverse out)))
                   ((= k i) (loop xs (+ k 1) (cons v (cons (car xs) out))))
                   (else (loop (cdr xs) (+ k 1) (cons (car xs) out))))))))
(nf-leaf! "Elixir.BeamLisp.PackageAuthority/sdk_unit_compiled?/1"
 (lambda (ns) (not (eq? (nf-ns-entry ns) native-missing))))

(nf-set-leaf! "Elixir.BeamLisp.Env/env_id/0" (lambda () (if nf-env-current nf-env-current (list (bl-key "global")))))
(nf-leaf! "Elixir.BeamLisp.Env/current_ns/0" (lambda () native-env-current))

;; ── Front-end diagnosis: host/nf-trace!/1 makes the next few host (Scheme)
;; conditions print the Scheme frames live at the raise, to stdout. Off by
;; default; front-end/stage.bl turns it on for a named-unit run.
(define nf-trace-left 0)
(define nf-trace-seen '())
(define (nf-trace-frames)
 (call/cc (lambda (here)
  (let loop ((o (inspect/object here)) (i 0) (out '()))
   (if (or (>= i 60) (not (eq? (o 'type) 'continuation))) (reverse out)
    (let* ((code (o 'code)) (name (and code (code 'name))))
     (loop (o 'link) (+ i 1) (if name (cons name out) out))))))))
(define nf-plain-catcher with-exception-catcher)
(set! with-exception-catcher
 (lambda (handler thunk)
  (if (<= nf-trace-left 0) (nf-plain-catcher handler thunk)
   ((call/cc (lambda (k)
     (with-exception-handler
      (lambda (e)
       (if (and (> nf-trace-left 0) (not (memq e nf-trace-seen))
                (or (not (native-raised? e))
                    (let ((r (vector-ref e 2))) (and (bl-tag? r 'tuple) (> (bl-count r) 1) (eq? (bl-nth r 0) (bl-key "badarg"))
                                                     (not (and (string? (bl-nth r 1)) (nf-string-prefix? "invalid UTF-8" (bl-nth r 1))))))))
        (let ((text (if (native-raised? e) (native-render (vector-ref e 2) #t)
                     (with-output-to-string "" (lambda () (display-exception e (current-output-port)))))))
         (set! nf-trace-seen (cons e nf-trace-seen))
         (set! nf-trace-left (- nf-trace-left 1))
         (display "NF-TRACE ") (write text) (display " ") (write (nf-trace-frames)) (newline)))
       (k (lambda () (handler e))))
      (lambda () (call-with-values thunk (lambda vs (lambda () (apply values vs))))))))))))
(define (nf-traced-resolve f xs)
 (let ((call (native-invoke-original-resolve f xs)))
  (let ((g (car call)))
   (if (not (or (procedure? g) (native-keyword? g) (bl-tag? g 'map) (bl-tag? g 'vec) (bl-tag? g 'set)))
    (begin (display "NF-NOT-CALLABLE ") (write (native-render g #t)) (display " ARGS ")
           (write (map (lambda (x) (native-render x #t)) (cdr call))) (newline)))
   call)))
(nf-leaf! "host/nf-trace!/1"
 (lambda (n) (set! nf-trace-left n)
  (set! native-resolve-call (if (> n 0) nf-traced-resolve native-invoke-original-resolve)) (bl-key "ok")))

;; ── Front end: Elixir Map over BL vectors and sets ──────────────────────────
;; On the BEAM a vector is %BeamLisp.Vector{items, meta} and a set is
;; %BeamLisp.Set{members}: plain maps to every Map function. Staging walks
;; compiler data with Map/to_list and rebuilds it with Map/new, so the native
;; Map leaves read a vector or set through its struct fields, and a map built
;; with a Vector or Set :__struct__ becomes that value again.
(define (nf-view m) (if (or (bl-tag? m 'vec) (bl-tag? m 'set) (native-opaque-struct? m)) (native-struct-fields m) m))
(define (nf-rebuild m)
 (let ((mod (if (bl-tag? m 'map) (native-raw-map-get m native-struct-key bl-nil) bl-nil)))
  (if (or (eq? mod native-vector-module-key) (eq? mod native-set-module-key))
   (bl-struct mod (native-raw-remove m native-struct-key)) m)))
(nf-set-leaf! "Elixir.Map/get/2" (lambda (m k) (native-raw-get (nf-view m) k)))
(nf-set-leaf! "Elixir.Map/get/3" (lambda (m k d) (native-raw-get (nf-view m) k d)))
(nf-set-leaf! "Elixir.Map/to_list/1" (lambda (m) (native-map-pairs (native-assert-map m))))
(nf-set-leaf! "Elixir.Map/has_key?/2" (lambda (m k) (native-raw-map-has? (nf-view m) k)))
(nf-set-leaf! "Elixir.Map/new/1" (lambda (xs) (nf-rebuild (h-bmap (native-finite-items xs)))))

;; ── Front end: crypto:hash(sha256, IoData) ─────────────────────────────────
;; Staging digests sources and compiler terms (term_to_binary bytes). FIPS
;; 180-4 over exact integers masked to 32 bits; the digest is a byte binary.
(define (nf-iodata-bytes x)
 (cond ((string? x) (native-utf8-bytes x))
  ((native-bytes? x) (bytevector->u8-list (vector-ref x 1)))
  ((and (integer? x) (exact? x)) (list x))
  ((null? x) '())
  ((pair? x) (append (nf-iodata-bytes (car x)) (nf-iodata-bytes (cdr x))))
  (else (native-badarg "iodata expected"))))
(define nf-sha256-k
 '#(#x428a2f98 #x71374491 #xb5c0fbcf #xe9b5dba5 #x3956c25b #x59f111f1 #x923f82a4 #xab1c5ed5
    #xd807aa98 #x12835b01 #x243185be #x550c7dc3 #x72be5d74 #x80deb1fe #x9bdc06a7 #xc19bf174
    #xe49b69c1 #xefbe4786 #x0fc19dc6 #x240ca1cc #x2de92c6f #x4a7484aa #x5cb0a9dc #x76f988da
    #x983e5152 #xa831c66d #xb00327c8 #xbf597fc7 #xc6e00bf3 #xd5a79147 #x06ca6351 #x14292967
    #x27b70a85 #x2e1b2138 #x4d2c6dfc #x53380d13 #x650a7354 #x766a0abb #x81c2c92e #x92722c85
    #xa2bfe8a1 #xa81a664b #xc24b8b70 #xc76c51a3 #xd192e819 #xd6990624 #xf40e3585 #x106aa070
    #x19a4c116 #x1e376c08 #x2748774c #x34b0bcb5 #x391c0cb3 #x4ed8aa4a #x5b9cca4f #x682e6ff3
    #x748f82ee #x78a5636f #x84c87814 #x8cc70208 #x90befffa #xa4506ceb #xbef9a3f7 #xc67178f2))
(define (nf-u32 x) (bitwise-and x #xffffffff))
(define (nf-rotr x n) (nf-u32 (bitwise-ior (arithmetic-shift x (- n)) (arithmetic-shift x (- 32 n)))))
(define (nf-sha256 bytes)
 (let* ((len (length bytes))
        (pad (let ((r (modulo (+ len 9) 64))) (if (= r 0) 0 (- 64 r))))
        (total (+ len 9 pad))
        (bv (make-bytevector total 0))
        (h (vector #x6a09e667 #xbb67ae85 #x3c6ef372 #xa54ff53a #x510e527f #x9b05688c #x1f83d9ab #x5be0cd19))
        (w (make-vector 64 0)))
  (let fill ((i 0) (xs bytes)) (if (pair? xs) (begin (bytevector-u8-set! bv i (car xs)) (fill (+ i 1) (cdr xs)))))
  (bytevector-u8-set! bv len #x80)
  (let put ((i 0)) (if (< i 8) (begin (bytevector-u8-set! bv (- total 1 i) (bitwise-and (arithmetic-shift (* 8 len) (* -8 i)) 255)) (put (+ i 1)))))
  (let block ((off 0))
   (if (< off total)
    (begin
     (let ws ((t 0))
      (if (< t 64)
       (begin
        (vector-set! w t
         (if (< t 16)
          (bitwise-ior (arithmetic-shift (bytevector-u8-ref bv (+ off (* 4 t))) 24) (arithmetic-shift (bytevector-u8-ref bv (+ off (* 4 t) 1)) 16)
                       (arithmetic-shift (bytevector-u8-ref bv (+ off (* 4 t) 2)) 8) (bytevector-u8-ref bv (+ off (* 4 t) 3)))
          (let* ((a (vector-ref w (- t 15))) (b (vector-ref w (- t 2)))
                 (s0 (bitwise-xor (nf-rotr a 7) (nf-rotr a 18) (arithmetic-shift a -3)))
                 (s1 (bitwise-xor (nf-rotr b 17) (nf-rotr b 19) (arithmetic-shift b -10))))
           (nf-u32 (+ (vector-ref w (- t 16)) s0 (vector-ref w (- t 7)) s1)))))
        (ws (+ t 1)))))
     (let round ((t 0) (a (vector-ref h 0)) (b (vector-ref h 1)) (c (vector-ref h 2)) (d (vector-ref h 3))
                 (e (vector-ref h 4)) (f (vector-ref h 5)) (g (vector-ref h 6)) (hh (vector-ref h 7)))
      (if (< t 64)
       (let* ((S1 (bitwise-xor (nf-rotr e 6) (nf-rotr e 11) (nf-rotr e 25)))
              (ch (bitwise-xor (bitwise-and e f) (bitwise-and (bitwise-xor e #xffffffff) g)))
              (t1 (nf-u32 (+ hh S1 ch (vector-ref nf-sha256-k t) (vector-ref w t))))
              (S0 (bitwise-xor (nf-rotr a 2) (nf-rotr a 13) (nf-rotr a 22)))
              (maj (bitwise-xor (bitwise-and a b) (bitwise-and a c) (bitwise-and b c)))
              (t2 (nf-u32 (+ S0 maj))))
        (round (+ t 1) (nf-u32 (+ t1 t2)) a b c (nf-u32 (+ d t1)) e f g))
       (for-each (lambda (i v) (vector-set! h i (nf-u32 (+ (vector-ref h i) v))))
        '(0 1 2 3 4 5 6 7) (list a b c d e f g hh))))
     (block (+ off 64)))))
  (let ((out (make-bytevector 32 0)))
   (let put ((i 0)) (if (< i 8) (begin
    (bytevector-u8-set! out (* 4 i) (arithmetic-shift (vector-ref h i) -24))
    (bytevector-u8-set! out (+ (* 4 i) 1) (bitwise-and (arithmetic-shift (vector-ref h i) -16) 255))
    (bytevector-u8-set! out (+ (* 4 i) 2) (bitwise-and (arithmetic-shift (vector-ref h i) -8) 255))
    (bytevector-u8-set! out (+ (* 4 i) 3) (bitwise-and (vector-ref h i) 255)) (put (+ i 1)))))
   out)))
(nf-set-leaf! "crypto/hash/2"
 (lambda (kind data)
  (if (eq? kind (bl-key "sha256")) (native-bytes (nf-sha256 (nf-iodata-bytes data)))
   (native-badarg "crypto:hash supports sha256 natively"))))
(nf-set-leaf! "Elixir.Enum/to_list/1" (lambda (xs) (if (nf-range? xs) (nf-range-items xs) (native-finite-items xs))))
;; Code.ensure_loaded?/1: a module this image carries (a native namespace's
;; module or a host leaf module); nothing is ever loaded on demand.
(define nf-ensure-seen '())
(nf-set-leaf! "Elixir.Code/ensure_loaded?/1"
 (lambda (mod)
  (let ((answer (erlang-module-loaded? mod)))
   (if (and (> nf-trace-left 0) (not (member mod nf-ensure-seen)))
    (begin (set! nf-ensure-seen (cons mod nf-ensure-seen))
     (display "NF-ENSURE-LOADED ") (write (native-render mod #t)) (display " ") (write answer) (newline)))
   answer)))
;; host/nf-route!/2: KEY (Module/function/arity) becomes a call of the BL
;; function F, and function_exported/3 answers true for it.
(nf-leaf! "host/nf-route!/2"
 (lambda (key f)
  (set! native-excluded-host-leaves (let loop ((xs native-excluded-host-leaves)) (cond ((null? xs) '()) ((equal? (car xs) key) (loop (cdr xs))) (else (cons (car xs) (loop (cdr xs)))))))
  (nf-set-leaf! key (lambda arguments (bl-invoke f arguments)))
  (bl-key "ok")))
;; Regex.match?/2 over the native regex runner; erlang:external_size/1 as
;; the length of this image's own term_to_binary (the BEAM's equals it for
;; the uncompressed default encoding).
(nf-set-leaf! "Elixir.Regex/match?/2" (lambda (regex text) (not (bl-is-nil (native-regex-run regex text)))))
(nf-set-leaf! "erlang/external_size/1"
 (lambda (x) (if (or (h-is-float x) (h-is-int x)) (native-external-number-size x)
              (dynamic-wind (lambda () (set! etf-measuring? #t))
                            (lambda () (bytevector-length (vector-ref (native-term-to-binary x) 1)))
                            (lambda () (set! etf-measuring? #f))))))
;; No publication happens natively: every namespace is at generation 0 of
;; :global, so declaration-query certificates are stable.
(nf-set-leaf! "Elixir.BeamLisp.Env/namespace_generations/1"
 (lambda (namespaces) (map (lambda (ns) (bl-make-tuple3 (bl-key "global") ns 0)) (native-finite-items namespaces))))
(define (bl-make-tuple3 a b c) (bl-tuple (list a b c)))
;; The SDK's checked declaration tables are the BEAM's (custody).
(nf-set-leaf! "Elixir.BeamLisp.PackageAuthority/sdk_checked_declaration_table/1"
 (lambda (ns) (native-raw-map-get (nf-world-get (bl-key "declaration-tables") (bl-empty-map)) ns bl-nil)))
;; String.replace_suffix/3 and replace_prefix/3 (byte-wise, as Elixir's).
(define (nf-string-suffix? p s)
 (and (>= (string-length s) (string-length p)) (string=? (substring s (- (string-length s) (string-length p)) (string-length s)) p)))
(nf-set-leaf! "Elixir.String/replace_suffix/3"
 (lambda (s match with) (if (nf-string-suffix? match s) (string-append (substring s 0 (- (string-length s) (string-length match))) with) s)))
(nf-set-leaf! "Elixir.String/replace_prefix/3"
 (lambda (s match with) (if (nf-string-prefix? match s) (string-append with (substring s (string-length match) (string-length s))) s)))
