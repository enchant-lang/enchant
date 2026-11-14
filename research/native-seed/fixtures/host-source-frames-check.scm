;; Append after pure host, compiler adapter, then optional source-frame helper.
(define (native-frame-check label ok)
 (if (not ok) (error (string-append "native source-frame check failed: " label))))
(define (native-test-source name line mode)
 (bl-map (bl-key "file") "source-fixture.bl" (bl-key "line") line
         (bl-key "col") 1 (bl-key "fn") name (bl-key "arity") 0 (bl-key "call") (bl-key mode)))
(define native-test-countdown #f)
(set! native-test-countdown (lambda (n)
 (bl-with-source-frame (native-test-source "countdown" 1 "direct")
  (lambda () (h-tick)
   (if (> n 0)
    (bl-source-call (native-test-source "countdown" 4 "tail") #t
     (lambda () (bl-invoke native-test-countdown (list (- n 1)))))
    (h-logical-stack))))))
(let* ((before native-max-frames) (frames (bl-invoke native-test-countdown '(5000))))
 (native-frame-check "tail source stack constant depth" (= 1 (length frames)))
 (native-frame-check "tail control stack max bounded" (<= native-max-frames (max before 1))))
(let ((continued? #f) (result #f))
 (bl-with-source-frame (native-test-source "host-caller" 10 "direct")
  (lambda ()
   (set! result
    (bl-source-call (native-test-source "host-caller" 12 "tail") #t
     (lambda () (bl-invoke (native-leaf "Elixir.Enum/map/2")
      (list '(1 2 3) (lambda (x)
       (bl-with-source-frame (native-test-source bl-nil 14 "direct") (lambda () (+ x 1)))))))))
   (set! continued? #t)))
 (native-frame-check "host callbacks do not inherit outer tail jump" (and continued? (equal? result '(2 3 4)))))
(let ((captured #f) (cleanup 0))
 (bl-with-source-frame (native-test-source "protected" 20 "direct")
  (lambda ()
   (bl-try (lambda ()
     (bl-source-call (native-test-source "protected" 22 "direct") #f
      (lambda () (bl-invoke (native-leaf "erlang/throw/1") '(7)))))
    (lambda (kind reason raw)
     (set! captured (and (eq? kind (bl-key "throw")) (= reason 7)
       (bl-tag? raw 'tuple) (pair? (bl-trace-frames raw)))))
    (lambda () (set! cleanup (+ 1 cleanup))))))
 (native-frame-check "raw and frame traces remain distinct" captured)
 (native-frame-check "protected cleanup once" (= cleanup 1)))
;; The raw BIF forwards to its target, never through a native callback fence.
(define native-test-raw-countdown #f)
(set! native-test-raw-countdown
 (bl-register-callable! (lambda (n)
  (bl-with-source-frame (native-test-source "raw-countdown" 30 "direct")
   (lambda ()
    (if (> n 0)
     (bl-source-call (native-test-source "raw-countdown" 31 "tail") #t
      (lambda () (native-raw-apply native-test-raw-countdown (list (- n 1)))))
     (h-logical-stack))))) 1))
(let ((frames
 (bl-with-source-frame (native-test-source "raw-caller" 40 "direct")
  (lambda ()
   (bl-source-call (native-test-source "raw-caller" 41 "tail") #t
    (lambda () (bl-invoke (native-leaf "erlang/apply/2") (list native-test-raw-countdown '(100)))))))))
 (native-frame-check "raw apply target tail frame remains bounded" (= 1 (length frames)))
 (native-frame-check "raw apply preserves actual target call site"
  (and (string=? (bl-get (car frames) (bl-key "fn")) "raw-countdown")
       (= (bl-get (car frames) (bl-key "line")) 31))))
(display "native source-frame checks passed") (newline)
