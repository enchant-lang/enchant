;; Smoke check of the new category-(b) host files over the host sources alone.
;; Run: bash research/native-seed/speed/data/smoke.sh
(define (L k) (native-leaf k))
(define t (let loop ((i 0) (t ((L "gb_trees/empty/0")))) (if (= i 40) t (loop (+ i 1) ((L "gb_trees/enter/3") (modulo (* i 7) 41) i t)))))
(display (bl-show ((L "gb_trees/size/1") t))) (newline)
(display (bl-show ((L "gb_trees/values/1") t))) (newline)
(display (bl-show ((L "gb_trees/lookup/2") 14 t))) (newline)
(display (bl-show ((L "gb_trees/smallest/1") t))) (display (bl-show ((L "gb_trees/largest/1") t))) (newline)
(define t2 ((L "gb_trees/delete/2") 14 t))
(display (bl-show ((L "gb_trees/is_defined/2") 14 t2))) (newline)
(display (bl-show ((L "gb_trees/next/1") ((L "gb_trees/iterator_from/2") 30 t2)))) (newline)
(display (bl-show ((L "Elixir.Keyword/get/2") (list (bl-make-tuple (bl-key "a") 1)) (bl-key "a")))) (newline)
(display (native-exception-message ((L "Elixir.KeyError/exception/1") (list (bl-make-tuple (bl-key "key") (bl-key "x")))))) (newline)
(display "DATA_SMOKE_OK") (newline)
