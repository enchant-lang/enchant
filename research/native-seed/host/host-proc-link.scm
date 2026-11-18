;; A checked compiled __bl_v call already carries its trailing rest list.
;; Select that descriptor arm directly; going through a module/leaf lookup
;; could pick an unrelated registered primitive with the same MFA spelling.
;; This is the shared callable representation ABI, with no actor policy.
(define (native-linked-packed-call value arguments)
 (if (and (native-multi-callable? value) (not (bl-is-nil (bl-nth value 2))))
  (bl-invoke (bl-nth (bl-nth value 2) 1) arguments)
  (error "checked native variadic entry is missing its descriptor arm")))
;; A call from source-frame code into a closure-prelude body. Prelude bodies
;; are compiled without source frames, so they never consume the pending
;; source call; the next source-frame function they reach (a callback, a lazy
;; thunk, the actor runtime's monitor or receive) would take it as its own. A
;; TAIL entry then makes that function replace the BL caller's frame and
;; return as the caller from inside the prelude body, skipping the rest of it
;; (a lazy force in tail position returned its monitor reference; see
;; speed/actor/RESULT.md). The tail entry is dropped at this boundary; a
;; non-tail entry is kept, so frame attribution is unchanged.
(define (native-drop-external-tail-site!)
 (let ((entry native-source-pending))
  (if (and entry (vector-ref entry 2)) (set! native-source-pending #f))))
(define (native-linked-external-call value arguments)
 (native-drop-external-tail-site!)
 (bl-invoke value arguments))
(define (native-linked-external-packed-call value arguments)
 (native-drop-external-tail-site!)
 (native-linked-packed-call value arguments))
