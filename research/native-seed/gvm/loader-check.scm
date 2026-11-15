;; Host ABI fixture only. Run with the compiled GVM host already loaded.
;; These explicit publisher contexts do not stand in for actual GVM modules.
(define gvm-loader-check-count 0)
(define (gvm-loader-check label value)
 (if (not value) (error "GVM loader ABI failed" label))
 (set! gvm-loader-check-count (+ gvm-loader-check-count 1)))
(define (gvm-loader-refuses thunk)
 (with-exception-catcher (lambda (failure) #t) (lambda () (thunk) #f)))
(define gvm-loader-fixture-manifest
 (bl-map (bl-key "schema") "bl.native.gvm-emission" (bl-key "version") 1
  (bl-key "runtime-abi") 1 (bl-key "module") "native_gvm_fixture"
  (bl-key "program-control") (bl-key "native-gvm")
  (bl-key "owner-globals") (bl-vec (list "native-gvm-unit/native_gvm_fixture/owner/p0"))
  (bl-key "authored-scheme") #f (bl-key "source-interpreter") #f
  (bl-key "anf-interpreter") #f (bl-key "gvm-interpreter") #f (bl-key "c-lambda-stepper") #f))
(gvm-loader-check 'abi1 (= (native-gvm-require-runtime-abi! 1) 1))
(gvm-loader-check 'abi2-refused (gvm-loader-refuses (lambda () (native-gvm-require-runtime-abi! 2))))
(gvm-loader-check 'abi-inexact-refused (gvm-loader-refuses (lambda () (native-gvm-require-runtime-abi! 1.0))))
(gvm-loader-check 'manifest (eq? gvm-loader-fixture-manifest
                            (native-gvm-validate-manifest! gvm-loader-fixture-manifest)))
(for-each (lambda (key)
 (gvm-loader-check key (gvm-loader-refuses (lambda ()
  (native-gvm-validate-manifest! (bl-assoc gvm-loader-fixture-manifest (bl-key key) #t))))))
 '("authored-scheme" "source-interpreter" "anf-interpreter" "gvm-interpreter" "c-lambda-stepper"))
(gvm-loader-check 'owners-required (gvm-loader-refuses (lambda ()
 (native-gvm-validate-manifest!
  (bl-assoc gvm-loader-fixture-manifest (bl-key "owner-globals") (bl-vec '()))))))
(for-each (lambda (name) (gvm-loader-check name (not (native-gvm-module-name? name))))
 '("" "/tmp/module" "../module" "0module" "a b" "a.b"))
(for-each (lambda (name) (gvm-loader-check name (native-gvm-module-name? name)))
 '("a" "native_gvm_u0000" "native_gvm_eval_2" "Pilot-2"))
(gvm-loader-check 'publisher-needs-load
 (gvm-loader-refuses (lambda () (native-gvm-publish-loaded! 42))))
(define gvm-loader-fixture-state (vector #t 0 bl-nil "fixture-not-a-module" gvm-loader-fixture-manifest))
(parameterize ((native-gvm-current-publisher gvm-loader-fixture-state))
 (gvm-loader-check 'nil-publishes (eq? (native-gvm-publish-loaded! bl-nil) bl-nil))
 (gvm-loader-check 'nil-seen (= (vector-ref gvm-loader-fixture-state 1) 1))
 (gvm-loader-check 'nil-value (eq? (vector-ref gvm-loader-fixture-state 2) bl-nil))
 (gvm-loader-check 'double-refused (gvm-loader-refuses (lambda () (native-gvm-publish-loaded! 42))))
 (vector-set! gvm-loader-fixture-state 0 #f)
 (gvm-loader-check 'stale-refused (gvm-loader-refuses (lambda () (native-gvm-publish-loaded! 42)))))
(gvm-loader-check 'outside-still-refused
 (gvm-loader-refuses (lambda () (native-gvm-publish-loaded! 42))))
(if (not (= gvm-loader-check-count 27)) (error "GVM loader ABI check count changed" gvm-loader-check-count))
(display "GVM_LOADER_HOST_ABI_PASS 27\n")
