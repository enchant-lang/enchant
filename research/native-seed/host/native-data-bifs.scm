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
