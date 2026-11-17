;; The driver supplies split-input, split-output, split-target and split-hard.
;; READ and WRITE transport real Scheme forms; no input form is evaluated.
;;
;; Cut points are content-defined, so an edit moves no boundary but its own.
;; Forms are grouped by definition: a group starts at a definition head
;; (`(define NAME ...)` or `(define (NAME ...) ...)`, NAME without `$`, so the
;; cells `v_X$1`, `v_X$g` and the registrations stay with their definition).
;; A unit may end only after a group, and it ends after group G when
;;   hash(NAME of G) < 2^32 * bucket(bytes of G) / split-mean
;; where bucket rounds down to a power of two. The decision reads only G's own
;; name and size class, never a position or a neighbour: editing a body
;; changes only the unit that holds it, unless the edit moves its group into
;; another power-of-two size class and so flips that one cut. Per byte, a cut
;; is equally likely everywhere, so big definitions do not form long runs.
;; Two bounds keep units valid:
;; - split-min: no natural cut before a unit holds split-min bytes;
;; - split-target: a unit never exceeds it (the drivers' gsc bound), except a
;;   single oversized form. When the next form would exceed it, the unit is
;;   cut before its STRONGEST group start (lowest score below), not at the
;;   overflow point, so an edit that moves the overflow point rarely moves
;;   the cut. Only a unit with no group start inside is cut at the overflow.
(define split-mean (quotient split-target 4))
(define split-min (quotient split-target 32))
(define (split-utf8-size text) (u8vector-length (string->utf8 text)))
(define (split-ffi? form)
 (and (pair? form)
  (cond ((memq (car form) '(c-declare c-lambda c-define)) #t)
        ((eq? (car form) 'quote) #f)
        (else (or (split-ffi? (car form)) (split-ffi? (cdr form)))))))
;; FNV-1a over the name's code points, 32 bits: stable across Gambit builds.
(define (split-name-hash name)
 (let loop ((i 0) (h 2166136261))
  (if (= i (string-length name)) h
   (loop (+ i 1)
         (modulo (* (bitwise-xor h (char->integer (string-ref name i))) 16777619) 4294967296)))))
(define (split-definition-name form)
 (and (pair? form) (eq? (car form) 'define) (pair? (cdr form))
  (let ((head (cadr form)))
   (let ((name (cond ((symbol? head) head)
                     ((and (pair? head) (symbol? (car head))) (car head))
                     (else #f))))
    (and name
     (let ((text (symbol->string name)))
      (let scan ((i 0))
       (cond ((= i (string-length text)) text)
             ((char=? (string-ref text i) #\$) #f)
             (else (scan (+ i 1)))))))))))
;; A group start's score: smaller is a stronger cut. The previous group ends
;; its unit naturally when the score is below 2^32 / split-mean. FNV's low k
;; bits depend only on the low k bits of each character, and ident names are
;; all digits and underscores, so the whole hash is compared.
(define (split-size-class bytes)
 (let loop ((c 1)) (if (> (* 2 c) bytes) c (loop (* 2 c)))))
(define (split-score name bytes) (/ (split-name-hash name) (split-size-class bytes)))
(define split-natural (/ 4294967296 split-mean))
(define split-group-name #f)
(define split-group-bytes 0)
(define split-index 0)
;; The current unit, NEWEST row first: #(text bytes score-or-#f).
(define split-rows '())
(define split-bytes 0)
(define (split-unit-bytes rows) (apply + (map (lambda (row) (vector-ref row 1)) rows)))
(define (split-write! rows)
 (let* ((name (string-append "forms-" (number->string split-index) ".scm"))
        (bytes (split-unit-bytes rows))
        (port (open-output-file (list path: (string-append split-output "/" name)
                                     char-encoding: 'UTF-8 eol-encoding: 'lf))))
  (for-each (lambda (row) (display (vector-ref row 0) port)) rows)
  (close-output-port port)
  (display "CHUNK\t") (display name) (display "\t")
  (display (length rows)) (display "\t") (display bytes) (display "\t")
  (display (if (> bytes split-target) 1 0)) (newline)
  (set! split-index (+ split-index 1))))
(define (split-flush)
 (if (pair? split-rows) (split-write! (reverse split-rows)))
 (set! split-rows '()) (set! split-bytes 0))
;; Cut the current unit before its strongest group start after the first row
;; (the earliest one on a tie); without one, write it whole.
(define (split-overflow!)
 (let ((rows (reverse split-rows)))
  (let find ((rest (cdr rows)) (at 1) (best #f) (best-at #f))
   (if (pair? rest)
    (let ((score (vector-ref (car rest) 2)))
     (if (and score (or (not best) (< score best)))
      (find (cdr rest) (+ at 1) score at)
      (find (cdr rest) (+ at 1) best best-at)))
    (if best-at
     (let take ((rest rows) (n best-at) (prefix '()))
      (if (= n 0)
       (begin (split-write! (reverse prefix))
              (set! split-rows (reverse rest)) (set! split-bytes (split-unit-bytes rest)))
       (take (cdr rest) (- n 1) (cons (car rest) prefix))))
     (split-flush))))))
(define (split-add! text size score)
 (if (and score (pair? split-rows) (< score split-natural) (>= split-bytes split-min))
  (split-flush))
 (let loop ()
  (if (and (pair? split-rows) (> (+ split-bytes size) split-target))
   (begin (split-overflow!) (loop))))
 (set! split-rows (cons (vector text size score) split-rows))
 (set! split-bytes (+ split-bytes size))
 (if (> split-bytes split-target) (split-flush)))
(define split-port (open-input-file (list path: split-input char-encoding: 'UTF-8)))
(let loop ()
 (let ((form (read split-port)))
  (if (eof-object? form)
   (begin (close-input-port split-port) (split-flush) (exit 0))
   (begin
    ;; Static C declarations and their c-lambda users stay in the separately
    ;; frozen host unit. Refuse an unaccounted FFI dependency across units.
    (if (split-ffi? form) (error "FFI outside indivisible frozen host unit"))
    (let* ((port (open-output-string))
           (text (begin (write form port) (newline port) (get-output-string port)))
           (size (split-utf8-size text))
           (head (split-definition-name form))
           (score (and head split-group-name (split-score split-group-name split-group-bytes))))
     (if (> size split-hard) (error "single Scheme form exceeds hard unit limit" size))
     (if head (begin (set! split-group-name head) (set! split-group-bytes 0)))
     (set! split-group-bytes (+ split-group-bytes size))
     (split-add! text size score))
    (loop)))))
