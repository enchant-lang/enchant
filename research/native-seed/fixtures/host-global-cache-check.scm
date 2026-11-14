;; Same pure-host/compiler process as host-compiler-cache-check.scm. These
;; checks exercise public selection behavior; registry state is restored.
(define native-global-cache-checks 0)
(define (native-global-cache-check label ok)
 (if (not ok) (error (string-append "native global-cache check failed: " label)))
 (set! native-global-cache-checks (+ native-global-cache-checks 1)))
(let ((saved-env native-env-rows) (saved-globals native-global-registry))
 (dynamic-wind
  (lambda () #f)
  (lambda ()
   (native-register! "core" "native-cache-fallback" 10)
   (native-global-cache-check "normal lookup follows core fallback"
    (= 10 (native-global "native.cache-user" "native-cache-fallback")))
   (native-global-cache-check "normal positive selection reused"
    (= 10 (native-global "native.cache-user" "native-cache-fallback")))
   (native-global-cache-check "exact key cannot reuse normal fallback"
    (eq? (native-fetch "native.cache-user" "native-cache-fallback" #t) (bl-key "error")))
   (native-register! "core" "native-cache-fallback" 11)
   (native-global-cache-check "compiled root redefinition refreshes fallback value"
    (= 11 (native-global "native.cache-user" "native-cache-fallback")))
   (native-intern "native.cache-user" "native-cache-fallback" 20)
   (native-global-cache-check "local source binding shadows cached core selection"
    (= 20 (native-global "native.cache-user" "native-cache-fallback")))
   (native-global-cache-check "exact resolves newly admitted local binding"
    (= 20 (native-global-exact "native.cache-user" "native-cache-fallback")))
   (native-intern "native.cache-user" "native-cache-fallback" 21)
   (native-global-cache-check "intern root change refreshes exact value"
    (= 21 (native-global-exact "native.cache-user" "native-cache-fallback")))
   ;; Refer targets have priority over implicit core, and exact follows only
   ;; the explicit refer chain. Replacing that chain must affect both modes.
   (native-register! "core" "native-cache-referred" 30)
   (native-intern "native.cache-provider-a" "native-cache-referred" 31)
   (native-intern "native.cache-provider-b" "native-cache-referred" 32)
   (native-global-cache-check "pre-refer normal selection is core"
    (= 30 (native-global "native.cache-importer" "native-cache-referred")))
   (native-env-put! (native-row (bl-key "refer") "native.cache-importer" "native-cache-referred")
    "native.cache-provider-a")
   (native-global-cache-check "new explicit refer replaces cached fallback"
    (= 31 (native-global "native.cache-importer" "native-cache-referred")))
   (native-global-cache-check "exact follows explicit refer chain"
    (= 31 (native-global-exact "native.cache-importer" "native-cache-referred")))
   (native-env-put! (native-row (bl-key "refer") "native.cache-importer" "native-cache-referred")
    "native.cache-provider-b")
   (native-global-cache-check "refer replacement updates normal selection"
    (= 32 (native-global "native.cache-importer" "native-cache-referred")))
   (native-global-cache-check "refer replacement updates exact selection"
    (= 32 (native-global-exact "native.cache-importer" "native-cache-referred")))
   ;; Qualified normal names consult the authored alias. Exact does not
   ;; acquire qualified-name or implicit-core behavior from a normal cache.
   (native-intern "native.cache-provider-a" "answer" 41)
   (native-intern "native.cache-provider-b" "answer" 42)
   (native-env-put! (native-row (bl-key "alias") "native.cache-alias-user" "p") "native.cache-provider-a")
   (native-global-cache-check "qualified lookup follows explicit alias"
    (= 41 (native-global "native.cache-alias-user" "p/answer")))
   (native-env-put! (native-row (bl-key "alias") "native.cache-alias-user" "p") "native.cache-provider-b")
   (native-global-cache-check "alias replacement invalidates qualified selection"
    (= 42 (native-global "native.cache-alias-user" "p/answer")))
   (native-global-cache-check "exact cache remains distinct for qualified spelling"
    (eq? (native-fetch "native.cache-alias-user" "p/answer" #t) (bl-key "error")))
   ;; Env and compiled roots have separate epochs but both can supersede a
   ;; previously selected compiled var. An explicitly present nil stays present.
   (native-register! "native.cache-live" "answer" 50)
   (native-global-cache-check "compiled local selection" (= 50 (native-global-exact "native.cache-live" "answer")))
   (native-register! "native.cache-live" "answer" 51)
   (native-global-cache-check "compiled local redefinition refreshes exact lookup"
    (= 51 (native-global-exact "native.cache-live" "answer")))
   (native-intern "native.cache-live" "answer" bl-nil)
   (native-global-cache-check "present nil shadows compiled positive value"
    (bl-is-nil (native-global-exact "native.cache-live" "answer")))
   (native-global-cache-check "missing binding initially absent"
    (eq? (native-fetch "native.cache-late" "answer" #t) (bl-key "error")))
   (native-intern "native.cache-late" "answer" 61)
   (native-global-cache-check "negative exact lookup does not stick after admission"
    (= 61 (native-global-exact "native.cache-late" "answer")))
   ;; Fetch preserves the raw macro value; only the public global wrappers
   ;; unwrap it, on both cold and warm cache paths.
   (let* ((macro (lambda (x) x)) (wrapped (bl-tuple (list (bl-key "$macro") macro))))
    (native-intern "native.cache-macros" "m" wrapped)
    (native-global-cache-check "raw fetch retains macro tuple" (eq? wrapped (native-fetch! "native.cache-macros" "m")))
    (native-global-cache-check "normal global unwraps cached macro tuple" (eq? macro (native-global "native.cache-macros" "m")))
    (native-global-cache-check "exact global unwraps macro tuple" (eq? macro (native-global-exact "native.cache-macros" "m"))))
   (let ((macro (lambda (x) (+ x 1))))
    (native-intern "native.cache-macros" "m" (bl-tuple (list (bl-key "$macro") macro)))
    (native-global-cache-check "macro redefinition refreshes unwrapped callable"
     (= 8 (bl-invoke (native-global-exact "native.cache-macros" "m") '(7))))))
  (lambda ()
   (set! native-env-rows saved-env)
   (set! native-global-registry saved-globals)
   (native-refresh-global-cache!))))
(display "native global-cache checks: ") (display native-global-cache-checks) (newline)
