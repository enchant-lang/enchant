;; A per-compiler-job experiment for three closed, string-only helpers. Calls
;; from running actors always retain the selected image's reduction behavior.
(define (name-slot ns)
 (##make-global-var
  (string->symbol (string-append "v" (apply string-append
    (map (lambda (c) (string-append "_" (number->string (char->integer c)))) (string->list ns))) "$1"))))
(define memo-rows
 (map (lambda (name)
       (let ((slot (name-slot name)))
        (vector name slot (##global-var-ref slot) (make-table test: equal?) 0 0 0)))
      '("compiler/split-slash" "native.scheme/ident" "native.scheme/text")))
(define (memo-reset!)
 (for-each (lambda (r) (vector-set! r 3 (make-table test: equal?)) (vector-set! r 4 0)) memo-rows))
(define (memo-entry row verify?)
 (let ((original (vector-ref row 2)))
  (lambda (x)
   (if (or seed-frame (not (string? x)) (> (string-length x) 128)) (original x)
    (let* ((tab (vector-ref row 3)) (prior (table-ref tab x #f)))
     (cond (prior
            (if verify?
                (begin
                 (vector-set! row 5 (+ 1 (vector-ref row 5)))
                 (if (not (bl-equal? prior (original x))) (error "different compiler result" x))))
            prior)
           (else (let ((result (original x)))
                   (if verify? (vector-set! row 6 (+ 1 (vector-ref row 6))))
                   (if (< (vector-ref row 4) 512)
                       (begin (table-set! tab (string-copy x) result)
                              (vector-set! row 4 (+ 1 (vector-ref row 4)))))
                   result))))))))
(define (memo-mode! mode)
 (for-each (lambda (r)
  (let ((compiler? (string=? (vector-ref r 0) "compiler/split-slash")))
   (if (or (member mode '("both" "verify"))
           (and compiler? (string=? mode "compile")) (and (not compiler?) (string=? mode "emit")))
       (##global-var-set! (vector-ref r 1) (memo-entry r (string=? mode "verify"))))))
  memo-rows))
(define (memo-report)
 (for-each (lambda (r) (display "MEMO ") (write (list (vector-ref r 0) (vector-ref r 5) (vector-ref r 6)))
                        (newline)) memo-rows))
