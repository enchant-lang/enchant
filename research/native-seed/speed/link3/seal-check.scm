;; N3 seal check on the real round-2 dev image body, with this worktree's host.
;; gsi -e '(load "/tmp/r3link/host.scm")' -e '(load "/tmp/r3link/image-body.scm")' seal-check.scm
(define checks 0)
(define (check name ok)
 (if (not ok) (begin (display "SEAL_CHECK_FAIL ") (display name) (newline) (exit 1)))
 (set! checks (+ checks 1)))
(define (raises? thunk)
 (call-with-current-continuation
  (lambda (k) (with-exception-handler (lambda (e) (k #t)) (lambda () (thunk) #f)))))
(define (leaf key) (bl-get native-leaf-registry key))
(define inc-before (bl-invoke (native-global "core" "inc") (list 41)))
(check "dev image runs compiled core/inc" (equal? 42 inc-before))
(check "dev image allows redefinition before seal"
 (not (raises? (lambda () ((leaf "Elixir.BeamLisp.Env/intern/3") "user" "probe" 1)))))
(check "seal succeeds: no Env row shadows a compiled definition" (eq? (bl-key "ok") (native-seal-image!)))
(check "sealed image still runs core/inc" (equal? 42 (bl-invoke (native-global "core" "inc") (list 41))))
(define old-inc (bl-get native-global-registry "core/inc"))
(check "native-register! of a compiled slot raises" (raises? (lambda () (native-register! "core" "inc" (lambda (x) 0)))))
(check "refused register restores the sealed value" (eq? old-inc (bl-get native-global-registry "core/inc")))
(check "refused register leaves calls on the sealed procedure" (equal? 42 (bl-invoke (native-global "core" "inc") (list 41))))
(check "Env/intern over a compiled slot raises" (raises? (lambda () ((leaf "Elixir.BeamLisp.Env/intern/3") "core" "inc" 0))))
(check "Env/intern over a seed raises" (raises? (lambda () ((leaf "Elixir.BeamLisp.Env/intern/3") "core" "+" 0))))
(check "Env/delete_key of a seed raises" (raises? (lambda () ((leaf "Elixir.BeamLisp.Env/delete_key/1") (native-row "core" "+")))))
(check "seed + still answers" (equal? 3 (bl-invoke (native-global "core" "+") (list 1 2))))
(check "refuse_sealed_redefinition! raises for a sealed slot"
 (raises? (lambda () ((leaf "Elixir.BeamLisp.Env/refuse_sealed_redefinition!/2") "core" "inc"))))
(check "refuse_sealed_redefinition! accepts a new name"
 (eq? (bl-key "ok") ((leaf "Elixir.BeamLisp.Env/refuse_sealed_redefinition!/2") "user" "fresh")))
(check "a new user var is still definable" (equal? 7 ((leaf "Elixir.BeamLisp.Env/intern/3") "user" "fresh" 7)))
(check "rebinding a non-sealed user var is still allowed" (equal? 8 ((leaf "Elixir.BeamLisp.Env/intern/3") "user" "probe" 8)))
(check "sealing twice raises" (raises? native-seal-image!))
(check "sealed_value answers :error natively" (eq? (bl-key "error") ((leaf "Elixir.BeamLisp.Env/sealed_value/3") "core" "inc" #t)))
(display "SEAL_CHECKS_PASSED ") (display checks) (newline)
(exit 0)
