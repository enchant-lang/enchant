;; Apply the runner's existing first-party result printer to the actual native
;; evaluation result. Errors remain visible in the host that produced them.
(let* ((bundle (native-eval-string (native-read-file (getenv "BOOT_BUNDLE"))))
       (install (native-global-exact "native.bootstrap" "install-source-macros!")))
  (bl-invoke install (list bundle))
  (let* ((eval-source (native-global-exact "native.eval" "eval-string"))
         (value (bl-invoke eval-source (list (native-read-file (getenv "BOOT_PROGRAM")) (getenv "BOOT_LABEL"))))
         (printed (bl-invoke (native-global-exact "rt" "print_str") (list value))))
    (display printed) (newline) (exit 0)))
