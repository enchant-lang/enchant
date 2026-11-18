;; Arguments: stage1 --eval native-startup-phases.scm bundle.scm
;; The outer bootstrap evaluates this observer after the compiled image starts.
;; It exits after running the same bundle and Source steps as ordinary --eval.
(define start (real-time))
(define bundle-text (native-read-file (caddr (native-command-line))))
(define read-end (real-time))
(define bundle (native-eval-string bundle-text))
(define decode-end (real-time))
(define install-source-macros (native-global-exact "native.bootstrap" "install-source-macros!"))
(bl-invoke install-source-macros (list bundle))
(define install-end (real-time))
(define eval-source (native-global-exact "native.eval" "eval-string"))
(bl-invoke eval-source (list "(println (+ 40 2))\n" "first-result.bl"))
(define eval-end (real-time))

(write (list 'STARTUP_PHASES
             (* 1000 (- read-end start))
             (* 1000 (- decode-end read-end))
             (* 1000 (- install-end decode-end))
             (* 1000 (- eval-end install-end))))
(newline)
(exit 0)
