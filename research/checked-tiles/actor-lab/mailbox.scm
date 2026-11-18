;; A skew-binary random-access list is a forest of complete binary trees.
;; A digit is (weight . tree). Visit a root before its two children. Only
;; the first two digits may have equal weight, so prepend and uncons each
;; touch at most two digits. Either a leaf or a node stores its value at 0.
(define (digits-push value ds)
  (if (and (pair? ds) (pair? (cdr ds)) (= (caar ds) (caadr ds)))
      (cons (cons (+ 1 (* 2 (caar ds))) (vector value (cdar ds) (cdadr ds))) (cddr ds))
      (cons (cons 1 (vector value)) ds)))

(define (digits-pop ds)
  (let ((weight (caar ds)) (tree (cdar ds)))
    (if (= weight 1) (cdr ds)
        (let ((half (quotient weight 2)))
          (cons (cons half (vector-ref tree 1))
                (cons (cons half (vector-ref tree 2)) (cdr ds)))))))

(define (digits-ref ds index)
  (let ((weight (caar ds)))
    (if (>= index weight) (digits-ref (cdr ds) (- index weight))
        (let descend ((tree (cdar ds)) (w weight) (i index))
          (if (= i 0) (vector-ref tree 0)
              (let ((half (quotient w 2)))
                (if (<= i half)
                    (descend (vector-ref tree 1) half (- i 1))
                    (descend (vector-ref tree 2) half (- i half 1)))))))))

;; [total, front length, front in FIFO order, rear in reverse FIFO order].
;; Nothing reachable from an old root is ever mutated.
(define lab-candidate? #f)
(define lab-base-slots 0)
(define lab-transfers 0)
(define lab-heads 0)
(define lab-interior 0)

(define (lab-empty) (if lab-candidate? (vector 0 0 '() '()) (bl-make-vec)))
(define (lab-size q) (if lab-candidate? (vector-ref q 0) (h-vec-size q)))

(define (lab-ref q i)
  (if (not lab-candidate?) (h-vec-el q i)
      (let ((n (vector-ref q 0)) (front (vector-ref q 1)))
        (cond ((or (< i 0) (>= i n)) (error "mailbox index out of range" i))
              ((< i front) (digits-ref (vector-ref q 2) i))
              (else (digits-ref (vector-ref q 3) (- n 1 i)))))))

(define (lab-append q x)
  (if (not lab-candidate?) (bl-invoke (native-global-exact "rt" "conj") (list q x))
      (vector (+ 1 (vector-ref q 0)) (vector-ref q 1) (vector-ref q 2)
              (digits-push x (vector-ref q 3)))))

(define (digits-reverse rear front)
  (if (null? rear) front
      (begin (set! lab-transfers (+ 1 lab-transfers))
             (digits-reverse (digits-pop rear) (digits-push (vector-ref (cdar rear) 0) front)))))

(define (lab-remove q i)
  (let ((n (lab-size q)))
    (cond ((or (< i 0) (>= i n)) (error "mailbox index out of range" i))
          ((not lab-candidate?)
           ;; Exact input length of the original native rebuild loop.
           (set! lab-base-slots (+ lab-base-slots n))
           (h-vec-remove q i))
          ((= i 0)
           (set! lab-heads (+ lab-heads 1))
           (let ((nf (vector-ref q 1)) (rear (vector-ref q 3)))
             (if (> nf 0)
                 (vector (- n 1) (- nf 1) (digits-pop (vector-ref q 2)) rear)
                 (vector (- n 1) (- n 1) (digits-pop (digits-reverse rear '())) '()))))
          (else
           ;; Deliberately simple selective removal. Keep and measure the worst case.
           (let copy ((j 0) (dest (lab-empty)))
             (if (= j n) dest
                 (begin (set! lab-interior (+ lab-interior 1))
                        (copy (+ j 1) (if (= i j) dest (lab-append dest (lab-ref q j)))))))))))
