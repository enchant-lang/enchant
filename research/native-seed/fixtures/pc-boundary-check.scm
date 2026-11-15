;; Standalone compiled C ABI probe. The private nil sentinel only supplies
;; BLC_CONST(m,0)'s equality contract; no language implementation is loaded.
(c-declare "#include \"pc-boundary-probe.c\"")
(define pc-probe-old (c-lambda (scheme-object int) int "pc_probe_original"))
(define pc-probe-new (c-lambda (scheme-object int) int "pc_probe_local"))
(define pc-probe-nil (list 'pc-probe-private-nil))
(define pc-probe-checks 0)
(define (pc-probe-check label ok)
 (if (not ok) (error "C local PC boundary mismatch" label))
 (set! pc-probe-checks (+ pc-probe-checks 1)))
(define (pc-probe-machine pc truth)
 (let* ((payload (vector 'payload '(4 5)))
        (constants (vector pc-probe-nil payload truth '(2 3) '(101 6 (1) source) '(call-site)))
        (unit (vector #f constants '#()))
        (frame (vector '() payload truth payload pc-probe-nil pc-probe-nil)))
  (vector unit pc frame '() pc-probe-nil 0 0 '() #f pc-probe-nil
          '() pc-probe-nil 0 #f)))
(define (pc-probe-run pc truth kind expected-pc expected-action)
 (let ((old (pc-probe-machine pc truth)) (new (pc-probe-machine pc truth)))
  (##gc)
  ;; No Scheme dispatcher or callback runs between these C-step returns and
  ;; the machine inspection below. The C functions never call Scheme.
  (let ((a (pc-probe-old old kind)) (b (pc-probe-new new kind)))
   (pc-probe-check 'same-action (and (= a expected-action) (= b expected-action)))
   (pc-probe-check 'exact-pc-before-host-dispatch
    (and (= (vector-ref old 1) expected-pc) (= (vector-ref new 1) expected-pc)))
   (pc-probe-check 'complete-rooted-machine-state (equal? old new)))))
(for-each
 (lambda (truth)
  (for-each (lambda (kind)
   (pc-probe-run 0 truth kind (if (or (eq? truth #f) (eq? truth pc-probe-nil)) 53 47) kind))
   '(1 2 3 4 5 6)))
 (list #t #f pc-probe-nil 0))
(for-each (lambda (pc)
 (for-each (lambda (kind) (pc-probe-run pc #t kind (if (= pc 53) 53 47) kind)) '(1 2 3 4 5 6)))
 '(11 47 53))
(for-each (lambda (pc) (pc-probe-run pc #t 1 pc -1))
 (list -1 99 (+ (expt 2 40) 99)))
;; Truncation reaches case47, but the saved diagnostic PC must retain every
;; original fixnum bit when no pure edge changed it. This rejects an int local.
(for-each (lambda (kind) (pc-probe-run (+ (expt 2 40) 47) #t kind (+ (expt 2 40) 47) kind))
 '(1 2 3 4 5 6))
(if (not (= pc-probe-checks 153)) (error "C local PC probe coverage changed" pc-probe-checks))
(display "NATIVE_C_LOCAL_PC_BOUNDARIES_PASS 153") (newline)
