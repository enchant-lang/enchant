;; All authored original actor/core bodies are static C-control objects. The
;; metadata loader evaluates owned constructors directly and needs no Source
;; or ANF text evaluation service. Any hidden authored-Scheme fallback fails.
(if (not (eq? native-c-backend (bl-key "c")))
 (error "original direct actor gate requires backend:c"))
(define native-direct-actor-original-eval-scheme (native-leaf "host/eval-scheme/1"))
(if (eq? native-direct-actor-original-eval-scheme native-missing)
 (error "direct actor gate expected the existing eval-scheme host leaf"))
(define native-direct-actor-refuse-scheme
 (native-c-replace-leaf! "host/eval-scheme/1" native-direct-actor-original-eval-scheme
  (lambda (source) (error "authored Scheme fallback is forbidden in the direct actor gate")) 1))
