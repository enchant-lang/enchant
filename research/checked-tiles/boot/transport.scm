;; Candidate for native-read-file. Use the same text port, encoding and EOF
;; conventions. Gambit's #f delimiter consumes the remaining input as one text.
(define (boot-bulk-read-file path)
  (call-with-input-file path
    (lambda (port)
      (let ((text (read-line port #f)))
        (if (eof-object? text) "" text)))))
