;; Append after the actual immutable canonical compiler bundle is installed.
;; This invokes the owning BL guard, not a native imitation or reduced gate.
(let ((guard (native-remote "Elixir.BeamLisp.CompilerData/check_first_order!/2")))
 (for-each (lambda (count)
  (let ((value (bl-vec (let loop ((i (- count 1)) (out '()))
                     (if (< i 0) out (loop (- i 1) (cons i out)))))))
   (bl-invoke guard (list value (bl-empty-map))))) '(33 1057))
 (let ((refused #f)
       (forged (bl-map (bl-key "__struct__") (bl-key "Elixir.BeamLisp.Vector")
                (bl-key "items") (bl-tuple (native-repeat 33 0)) (bl-key "meta") bl-nil)))
  (with-exception-catcher (lambda (e) (set! refused #t))
   (lambda () (bl-invoke guard (list forged (bl-empty-map)))))
  (if (not refused) (error "canonical CompilerData accepted oversized dense Vector storage"))))
(display "canonical CompilerData vector checks passed") (newline)
