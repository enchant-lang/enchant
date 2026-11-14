;; Append to the existing pure-host extra fixture process. Names cross the
;; actual raw atom/string boundary, including normalized atoms and UTF16 gaps.
(define native-symbol-name-checks 0)
(define (native-symbol-name-check label ok)
 (if (not ok) (error (string-append "native symbol-name check failed: " label)))
 (set! native-symbol-name-checks (+ native-symbol-name-checks 1)))
(let* ((name "Elixir.SymbolName/λ😀") (atom (bl-key name))
       (cold (native-atom-name atom)) (warm (native-atom-name atom)))
 (native-symbol-name-check "Unicode atom name cold" (string=? name cold))
 (native-symbol-name-check "Unicode atom name warm" (string=? name warm))
 (native-symbol-name-check "raw atom_to_binary unary retains Unicode value"
  (string=? name (bl-invoke (native-leaf "erlang/atom_to_binary/1") (list atom))))
 (native-symbol-name-check "raw atom_to_binary UTF8 retains Unicode value"
  (string=? name (bl-invoke (native-leaf "erlang/atom_to_binary/2") (list atom (bl-key "utf8")))))
 (native-symbol-name-check "raw binary atom roundtrip"
  (eq? atom (bl-invoke (native-leaf "erlang/binary_to_atom/1") (list warm))))
 (let ((map (bl-map atom 7 (bl-key "other") 8)))
  (native-symbol-name-check "warmed atom key finds original map value" (= 7 (bl-get map (bl-key name))))))
(native-symbol-name-check "true atom normalization" (string=? "true" (native-atom-name #t)))
(native-symbol-name-check "false atom normalization" (string=? "false" (native-atom-name #f)))
(native-symbol-name-check "nil atom normalization" (string=? "nil" (native-atom-name bl-nil)))
(native-symbol-name-check "empty atom name remains empty" (string=? "" (native-atom-name (bl-key ""))))
(native-symbol-name-check "keyword spelling distinguishes normalized true atom"
 (and (eq? (bl-key "true") #t) (string=? "true-extra" (native-atom-name (bl-key "true-extra")))))
(let* ((fragment (h-str-slice "😀" 0 1)) (atom (h-kw fragment))
       (name (native-atom-name atom)))
 (native-symbol-name-check "UTF16 fragment keyword remains a string" (h-is-str name))
 (native-symbol-name-check "UTF16 fragment keyword retains lone surrogate"
  (equal? '(55357) (h-str-codepoints name)))
 (native-symbol-name-check "UTF16 fragment name roundtrip" (bl-equal? atom (h-kw name)))
 (let ((refused #f))
  (with-exception-catcher (lambda (e) (set! refused #t)) (lambda () (native-utf8-bytes name)))
  (native-symbol-name-check "UTF16 fragment still refuses raw UTF8 boundary" refused)))
(display "native symbol-name checks: ") (display native-symbol-name-checks) (newline)
