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
   (let ((public (native-fetch "native.cache-live" "answer" #t)))
    (native-global-cache-check "public fetch preserves tagged present nil"
     (and (bl-tag? public 'tuple) (= 2 (bl-count public))
          (eq? (bl-nth public 0) (bl-key "ok")) (bl-is-nil (bl-nth public 1)))))
   (let ((refused #f))
    (with-exception-catcher (lambda (e) (set! refused #t))
     (lambda () (native-fetch! "native.cache-raw-missing" "answer" #t)))
    (native-global-cache-check "raw internal fetch still raises for absence" refused))
   (native-intern "native.cache-raw-missing" "answer" (bl-key "error"))
   (native-global-cache-check "present error atom is a value, not an absent binding"
    (eq? (native-fetch! "native.cache-raw-missing" "answer" #t) (bl-key "error")))
   (native-intern "native.cache-raw-missing" "answer" 62)
   (native-global-cache-check "fetch bang follows new epoch after prior absent lookup"
    (= 62 (native-fetch! "native.cache-raw-missing" "answer" #t)))
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
(let ((saved native-env-rows))
 (dynamic-wind (lambda () #f)
  (lambda ()
   (native-global-cache-check "raw foreign macro probe declines"
    (not (native-maybe-load-macro "erlang" "length")))
   (native-global-cache-check "unknown macro provider probe declines"
    (not (native-maybe-load-macro "not.in.closed.bundle" "missing")))
   (native-declare-ns "native.loader-probe")
   (native-intern "native.loader-probe" "ordinary" (lambda (x) x))
   (native-global-cache-check "known ordinary provider member is not macro"
    (not (native-maybe-load-macro "native.loader-probe" "ordinary")))
   (native-intern "native.loader-probe" "macro"
    (bl-tuple (list (bl-key "$macro") (lambda (x) x))))
   (native-global-cache-check "actual macro binding is recognized"
    (native-maybe-load-macro "native.loader-probe" "macro")))
  (lambda () (set! native-env-rows saved))))
;; Canonical Env.link_owner differs deliberately from Env.link: a VALUE at
;; an earlier candidate blocks the former's later core-link fallback.
(let ((saved-env native-env-rows) (saved-globals native-global-registry))
 (dynamic-wind (lambda () #f)
  (lambda ()
   (let* ((owner (native-remote "Elixir.BeamLisp.Env/link_owner/2"))
          (link (native-remote "Elixir.BeamLisp.Env/link/2"))
          (delete (native-remote "Elixir.BeamLisp.Env/delete_key/1"))
          (ns "native.owner-private")
          (core-info (bl-tuple (list (bl-key "Elixir.BeamLisp.Ns.Rt")
                       (bl-map 2 (bl-key "map")) (bl-tuple (list 2 (bl-key "map_multi"))))))
          (own-info (bl-tuple (list (bl-key "native.owner.private.module")
                      (bl-map 2 (bl-key "private_map")) bl-nil)))
          (core-owner (bl-tuple (list (bl-key "ok") "core" core-info)))
          (core-link (bl-tuple (list (bl-key "ok") core-info)))
          (private-map (lambda (f xs) (bl-key "private-eager-map"))))
    (native-env-put! (native-row (bl-key "link") "core" "map") core-info)
    (native-global-cache-check "link_owner initially selects core map link"
     (h-eq (bl-invoke owner (list ns "map")) core-owner))
    (native-register! ns "map" private-map)
    (native-put-meta ns "map" (bl-map (bl-key "private") #t))
    (native-global-cache-check "private compiled map stops core link_owner fallback"
     (eq? (bl-invoke owner (list ns "map")) (bl-key "error")))
    (native-global-cache-check "plain link preserves links-only core fallback behind private value"
     (h-eq (bl-invoke link (list ns "map")) core-link))
    (native-global-cache-check "refused direct shortcut leaves actual private function selected"
     (eq? (native-global ns "map") private-map))
    (set! native-global-registry (native-map-remove native-global-registry (string-append ns "/map")))
    (native-global-cache-check "deleting compiled local value restores core link_owner fallback"
     (h-eq (bl-invoke owner (list ns "map")) core-owner))
    (native-intern ns "map" bl-nil)
    (native-global-cache-check "present nil value stops core link_owner fallback"
     (eq? (bl-invoke owner (list ns "map")) (bl-key "error")))
    (native-global-cache-check "plain link still falls through present nil value"
     (h-eq (bl-invoke link (list ns "map")) core-link))
    (native-intern ns "map" #f)
    (native-global-cache-check "present false value stops core link_owner fallback"
     (eq? (bl-invoke owner (list ns "map")) (bl-key "error")))
    (native-env-put! (native-row (bl-key "link") ns "map") own-info)
    (native-global-cache-check "exact own link takes precedence over its value for link_owner"
     (h-eq (bl-invoke owner (list ns "map")) (bl-tuple (list (bl-key "ok") ns own-info))))
    (native-global-cache-check "plain link also gives exact own link precedence"
     (h-eq (bl-invoke link (list ns "map")) (bl-tuple (list (bl-key "ok") own-info))))
    (bl-invoke delete (list (native-row (bl-key "link") ns "map")))
    (native-global-cache-check "deleting own link reveals the existing value barrier"
     (eq? (bl-invoke owner (list ns "map")) (bl-key "error")))
    (bl-invoke delete (list (native-row ns "map")))
    (native-global-cache-check "deleting live local value restores core link_owner fallback"
     (h-eq (bl-invoke owner (list ns "map")) core-owner))
    (native-intern "native.owner-provider" "map" 17)
    (native-env-put! (native-row (bl-key "refer") "native.owner-importer" "map") "native.owner-provider")
    (native-global-cache-check "explicit referred value also blocks later core link_owner fallback"
     (eq? (bl-invoke owner (list "native.owner-importer" "map")) (bl-key "error")))
    (native-global-cache-check "plain link retains canonical fallback behind a referred value"
     (h-eq (bl-invoke link (list "native.owner-importer" "map")) core-link))
    (native-env-put! (native-row (bl-key "link") "native.owner-provider" "map") own-info)
    (native-global-cache-check "referred own link wins over that provider's value"
     (h-eq (bl-invoke owner (list "native.owner-importer" "map"))
      (bl-tuple (list (bl-key "ok") "native.owner-provider" own-info))))
    (bl-invoke delete (list (native-row (bl-key "link") "native.owner-provider" "map")))
    (bl-invoke delete (list (native-row "native.owner-provider" "map")))
    (native-global-cache-check "deleting referred link and value restores core fallback"
     (h-eq (bl-invoke owner (list "native.owner-importer" "map")) core-owner))))
  (lambda ()
   (set! native-env-rows saved-env)
   (set! native-global-registry saved-globals)
   (native-refresh-global-cache!))))

(display "native global-cache checks: ") (display native-global-cache-checks) (newline)
