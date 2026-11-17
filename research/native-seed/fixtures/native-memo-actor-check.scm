;; memo-actor-check.scm — native-memo.scm's actor-runtime plumbing (round-3 X).
;; Appended after host.scm, host-values, host-leaves, host-extra and
;; native-memo.scm (check-host.py's memo composition). No compiled actor
;; runtime is loaded here, so `native-fetch-value` — host-compiler.scm's Env
;; lookup — is a stand-in that answers recording procedures for the five
;; `native.kernel` names native-memo.scm calls. The real runtime is exercised
;; by speed/actor/lazy-actors.bl.
(define memo-actor-checks 0)
(define (memo-actor-check label ok)
 (if (not ok) (error (string-append "memo actor check failed: " label)))
 (set! memo-actor-checks (+ memo-actor-checks 1)))
(define memo-actor-calls '())
(define memo-actor-alive '())
(define memo-actor-runtime? #f)
(define (memo-actor-pid n) (bl-vec (list (bl-key "pid") 1 n)))
(define (memo-actor-record! name . arguments)
 (set! memo-actor-calls (cons (cons name arguments) memo-actor-calls)) (bl-key "recorded"))
(define (native-fetch-value ns name exact?)
 (if (not (and memo-actor-runtime? (string=? ns "native.kernel"))) native-missing
  (cond ((string=? name "rt-alive?") (lambda (pid) (if (member pid memo-actor-alive) #t #f)))
   ((string=? name "rt-pid?") (lambda (x) (and (bl-tag? x 'vec) (= 3 (bl-count x)) (eq? (bl-nth x 0) (bl-key "pid")))))
   ((member name '("native-monitor!" "native-demonitor!" "native-send!"))
    (lambda arguments (apply memo-actor-record! name arguments)))
   (else native-missing))))
(define (memo-leaf key) (native-leaf key))
(define (memo-refuses? thunk)
 (with-exception-catcher (lambda (e) #t) (lambda () (thunk) #f)))
(define waits (bl-key "bl_lazy_waits_on"))
(define item (bl-make-tuple (bl-key "dictionary") waits))
;; The compiler image: no actor runtime, self nil, one dictionary.
(h-set-self bl-nil)
((memo-leaf "erlang/put/2") waits 7)
(memo-actor-check "no runtime: self's dictionary through process_info"
 (bl-key-equal? (bl-make-tuple item 7) ((memo-leaf "erlang/process_info/2") bl-nil item)))
(memo-actor-check "no runtime: another pid is undefined"
 (eq? (bl-key "undefined") ((memo-leaf "erlang/process_info/2") (memo-actor-pid 9) item)))
(memo-actor-check "no runtime: is_pid keeps its answer" (eq? #f ((memo-leaf "erlang/is_pid/1") (memo-actor-pid 9))))
(memo-actor-check "no runtime: monitor refuses"
 (memo-refuses? (lambda () ((memo-leaf "Elixir.Process/monitor/1") (memo-actor-pid 9)))))
(memo-actor-check "no runtime: a notification refuses"
 (memo-refuses? (lambda () (native-memo-notify! (list (bl-make-tuple (memo-actor-pid 9) 1))))))
;; An actor program: each actor has its own dictionary.
(set! memo-actor-runtime? #t)
(define a (memo-actor-pid 1))
(define b (memo-actor-pid 2))
(set! memo-actor-alive (list a b))
(h-set-self a)
(memo-actor-check "a fresh actor dictionary is empty" (eq? (bl-key "undefined") ((memo-leaf "erlang/get/1") waits)))
((memo-leaf "erlang/put/2") waits b)
(h-set-self b)
(memo-actor-check "another actor does not see it" (eq? (bl-key "undefined") ((memo-leaf "erlang/get/1") waits)))
(memo-actor-check "process_info reads a live actor's dictionary"
 (bl-key-equal? (bl-make-tuple item b) ((memo-leaf "erlang/process_info/2") a item)))
(memo-actor-check "process_info of a missing key is undefined inside the item"
 (bl-key-equal? (bl-make-tuple item (bl-key "undefined")) ((memo-leaf "erlang/process_info/2") b item)))
(h-set-self bl-nil)
(memo-actor-check "the root dictionary is separate" (eqv? 7 ((memo-leaf "erlang/get/1") waits)))
(set! memo-actor-alive (list b))
(memo-actor-check "a dead actor is undefined" (eq? (bl-key "undefined") ((memo-leaf "erlang/process_info/2") a item)))
(set! memo-actor-alive (list a b))
(memo-actor-check "a dead actor's dictionary is dropped"
 (bl-key-equal? (bl-make-tuple item (bl-key "undefined")) ((memo-leaf "erlang/process_info/2") a item)))
(memo-actor-check "is_pid answers actor pids" (and ((memo-leaf "erlang/is_pid/1") a) (not ((memo-leaf "erlang/is_pid/1") 3))))
(h-set-self b)
((memo-leaf "Elixir.Process/monitor/1") a)
((memo-leaf "Elixir.Process/demonitor/2") (bl-key "ref") (list (bl-key "flush")))
(native-memo-notify! (list (bl-make-tuple a (bl-make-tuple (bl-key "lazy_attempt") 1))))
(memo-actor-check "monitor, demonitor and notify are the runtime's operations"
 (equal? (reverse memo-actor-calls)
  (list (list "native-monitor!" (bl-key "process") a)
        (list "native-demonitor!" (bl-key "ref") (list (bl-key "flush")))
        (list "native-send!" a (bl-make-tuple (bl-key "lazy_attempt") 1)))))
(h-set-self bl-nil)
(display "memo actor checks: ") (display memo-actor-checks) (newline)
