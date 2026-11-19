;; Candidate for native-read-file. Use the same text port, encoding and EOF
;; conventions. Gambit's #f delimiter consumes the remaining input as one text.
(define (boot-bulk-read-file path)
  (call-with-input-file path
    (lambda (port)
      (let ((text (read-line port #f)))
        (if (eof-object? text) "" text)))))

;; Keep the original decoder and its read-char failure site on a single open
;; port. Assemble text in blocks to avoid two temporary list cells per character.
(define (boot-block-read-file path)
  (call-with-input-file path
    (lambda (port)
      (let ((capacity 4096))
        (let loop ((chunk (make-string capacity)) (used 0) (previous '()))
          (let ((ch (read-char port)))
            (cond ((eof-object? ch)
                   (let ((last (substring chunk 0 used)))
                     (if (null? previous) last
                         (apply string-append (reverse (cons last previous))))))
                  ((= used capacity)
                   (let ((next (make-string capacity)))
                     (string-set! next 0 ch)
                     (loop next 1 (cons chunk previous))))
                  (else (string-set! chunk used ch)
                        (loop chunk (+ used 1) previous)))))))))
