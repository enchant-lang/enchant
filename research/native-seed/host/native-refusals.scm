;; Named refusals for remotes the compiled service namespaces mention but the
;; native image cannot honour (host-compiler.scm: native-service-refusals).
;; This file loads LAST: a key that any host file provides keeps that provider.
(for-each (lambda (key)
  (if (not (native-map-has? native-leaf-registry key))
   (begin (set! native-excluded-host-leaves (cons key native-excluded-host-leaves))
          (native-add-leaf! key (native-unavailable key)))))
 native-service-refusals)
