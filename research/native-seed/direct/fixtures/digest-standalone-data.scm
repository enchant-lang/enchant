;; Owned dependency DATA probe, evaluated by the existing standalone compiler.
;; Exit before macro bootstrap; this is not a Source or compiler qualification.
(if (not (string=? (native-c-text-sha256 "abc")
 "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"))
 (error "standalone SHA256 ASCII contract"))
(if (not (string=? (native-c-text-sha256 "λ")
 "6bb5604cb68c1e249874295f9dad38394b818646a41a813af58598b72f0c221b"))
 (error "standalone SHA256 UTF8 contract"))
(display "NATIVE_DIRECT_STANDALONE_DIGEST_PASS 2\n")
(force-output)
(exit 0)
