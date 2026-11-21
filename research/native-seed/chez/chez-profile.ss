;; Sampling profiler for the Chez-hosted compiler. Every AB_TICKS engine ticks
;; the timer interrupt captures the current continuation and walks its frames
;; with the inspector, counting the code name of the leaf frame (self) and of
;; every distinct frame on the stack (inclusive). Load after the image, before
;; the observer; call (ab-profile-start!) and (ab-profile-stop! path).
(define ab-self (make-hashtable string-hash string=?))
(define ab-incl (make-hashtable string-hash string=?))
;; Anonymous closures have no code name; charge their samples to the nearest
;; named frame as well, so the leaf table is not dominated by "?".
(define ab-named (make-hashtable string-hash string=?))
;; "leaf <- caller": the leaf frame's name and the nearest named frame that
;; differs from it, to say which code drives a hot primitive.
(define ab-edges (make-hashtable string-hash string=?))
(define ab-samples 0)
(define ab-ticks (or (and (getenv "AB_TICKS") (string->number (getenv "AB_TICKS"))) 20000))
(define ab-profiling #f)
(define (ab-frame-names k depth)
  (let loop ((o (inspect/object k)) (n 0) (acc '()))
    (if (or (>= n depth) (not (eq? (o 'type) 'continuation)))
        (reverse acc)
        (let* ((code (o 'code)) (name (and code (code 'name))))
          (loop (o 'link) (+ n 1) (cons (if (string? name) name (format "~a" (or name "?"))) acc))))))
(define (ab-sample!)
  (call/cc
    (lambda (k)
      (let ((names (ab-frame-names k 64)))
        (set! ab-samples (+ ab-samples 1))
        ;; Drop the handler frames through Chez's interrupt trampoline.
        (let ((names (let skip ((ns names))
                       (cond ((null? ns) names)
                             ((string=? (car ns) "$event-and-resume") (cdr ns))
                             (else (skip (cdr ns)))))))
          (when (pair? names) (hashtable-update! ab-self (car names) add1 0))
          (let ((named (let find ((ns names)) (cond ((null? ns) #f) ((string=? (car ns) "?") (find (cdr ns))) (else (car ns))))))
            (when named (hashtable-update! ab-named named add1 0))
            (when named
              (let ((caller (let find ((ns names)) (cond ((null? ns) #f)
                                                         ((or (string=? (car ns) "?") (string=? (car ns) named)) (find (cdr ns)))
                                                         (else (car ns))))))
                (hashtable-update! ab-edges (string-append named " <- " (or caller "-")) add1 0))))
          (let ((seen (make-hashtable string-hash string=?)))
            (for-each (lambda (nm) (unless (hashtable-ref seen nm #f)
                                     (hashtable-set! seen nm #t)
                                     (hashtable-update! ab-incl nm add1 0))) names)))))))
(define (ab-profile-start!)
  (set! ab-profiling #t)
  (timer-interrupt-handler (lambda () (when ab-profiling (ab-sample!) (set-timer ab-ticks))))
  (set-timer ab-ticks))
(define (ab-top table n)
  (let-values (((ks vs) (hashtable-entries table)))
    (let ((rows (vector->list (vector-map cons ks vs))))
      (list-head (sort (lambda (a b) (> (cdr a) (cdr b))) rows) (min n (length rows))))))
(define (ab-profile-stop! path)
  (set! ab-profiling #f) (set-timer 0)
  (call-with-output-file path
    (lambda (p)
      (fprintf p "samples ~a\n== self\n" ab-samples)
      (for-each (lambda (r) (fprintf p "~a ~a\n" (cdr r) (car r))) (ab-top ab-self 70))
      (fprintf p "== nearest named\n")
      (for-each (lambda (r) (fprintf p "~a ~a\n" (cdr r) (car r))) (ab-top ab-named 70))
      (fprintf p "== leaf <- caller\n")
      (for-each (lambda (r) (fprintf p "~a ~a\n" (cdr r) (car r))) (ab-top ab-edges 120))
      (fprintf p "== inclusive\n")
      (for-each (lambda (r) (fprintf p "~a ~a\n" (cdr r) (car r))) (ab-top ab-incl 90)))
    '(replace)))
