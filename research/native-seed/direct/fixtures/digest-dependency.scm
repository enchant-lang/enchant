;; Tiny existing-host dependency probe. No compiler or BL body is loaded.
(define digest-probe-root (getenv "BL_NATIVE_C_UNIT_ROOT" #f))
(if (not digest-probe-root) (error "BL_NATIVE_C_UNIT_ROOT required"))
(load (string-append digest-probe-root "/host.o1"))
(if (not (string=? (native-c-text-sha256 "abc") "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")) (error "pinned SHA256/UTF8 host contract"))
(if (not (string=? (native-c-text-sha256 "λ") "6bb5604cb68c1e249874295f9dad38394b818646a41a813af58598b72f0c221b")) (error "pinned SHA256/UTF8 host contract"))
(display "NATIVE_DIRECT_DIGEST_DEPENDENCY_PASS 2\n") (force-output)
