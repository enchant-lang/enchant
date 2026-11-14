;; A checked compiled __bl_v call already carries its trailing rest list.
;; Select that descriptor arm directly; going through a module/leaf lookup
;; could pick an unrelated registered primitive with the same MFA spelling.
;; This is the shared callable representation ABI, with no actor policy.
(define (native-linked-packed-call value arguments)
 (if (and (native-multi-callable? value) (not (bl-is-nil (bl-nth value 2))))
  (bl-invoke (bl-nth (bl-nth value 2) 1) arguments)
  (error "checked native variadic entry is missing its descriptor arm")))
