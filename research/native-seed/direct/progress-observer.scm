;; Diagnostic only. Reads counters from an independent Gambit helper thread;
;; never replaces unit[0], after-step, h-tick, logical frames or any classifier.
(define c-progress-start (time->seconds (current-time)))
(define c-progress-phase 'source-bootstrap)
(define c-progress-reads 0)
(define c-progress-port (current-error-port))
(define (c-progress-line label values)
 (display label c-progress-port) (display " " c-progress-port)
 (write values c-progress-port) (newline c-progress-port) (force-output c-progress-port))
(define (c-progress-snapshot)
 (list (- (time->seconds (current-time)) c-progress-start)
       native-c-step-count native-c-noactor-ticks-elided
       native-c-pure-bif-seen native-c-pure-bif-steps))
(define (c-progress-report previous)
 (let* ((now (c-progress-snapshot)) (seconds (- (car now) (car previous)))
        (steps (- (cadr now) (cadr previous))))
  (c-progress-line "DIRECT_C_PROGRESS"
   (list (cons 'seconds (car now)) (cons 'steps (cadr now))
         (cons 'delta-steps steps) (cons 'steps-per-second (if (> seconds 0) (/ steps seconds) 0))
         (cons 'ticks-elided (caddr now)) (cons 'pure-bif-seen (cadddr now))
         (cons 'pure-bif-steps (car (cddddr now)))
         (cons 'reads c-progress-reads) (cons 'phase c-progress-phase)))
  now))
;; Replace only the exact current I/O LEAF. The native-read-file binding and
;; every eligibility dependency remain identical. host/ services resolve live.
(define c-progress-read-leaf (native-leaf "host/read-file/1"))
(if (eq? c-progress-read-leaf native-read-file)
 (native-c-replace-leaf! "host/read-file/1" c-progress-read-leaf
  (lambda (path)
   (set! c-progress-reads (+ c-progress-reads 1))
   (set! c-progress-phase (list 'reading path))
   (c-progress-line "DIRECT_C_READ_BEGIN"
    (list (- (time->seconds (current-time)) c-progress-start) path))
   (let ((answer (c-progress-read-leaf path)))
    (set! c-progress-phase (list 'read-complete path))
    (c-progress-line "DIRECT_C_READ_END"
     (list (- (time->seconds (current-time)) c-progress-start) path)) answer)) 1)
 (c-progress-line "DIRECT_C_READ_UNWRAPPED" '(current-leaf-is-not-native-read-file)))
(c-progress-line "DIRECT_C_PROGRESS_START"
 (list (cons 'interval 15) (cons 'samples 2)
       (cons 'pure-enabled native-c-pure-bif-enabled?)
       (cons 'tick-enabled native-c-noactor-tick-enabled?)))
(define c-progress-thread
 (thread-start!
  (make-thread
   (lambda ()
    (let loop ((remaining 2) (previous (c-progress-snapshot)))
     (if (> remaining 0)
      (begin (thread-sleep! 15)
       (loop (- remaining 1) (c-progress-report previous))))))
   'native-c-counter-observer)))
;; Original guarded proof and Source bundle bytes follow as the final value.
