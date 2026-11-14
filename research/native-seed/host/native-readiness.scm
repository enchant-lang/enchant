;; Native POSIX input producer. Append immediately after native-posix.scm in
;; the indivisible FFI host. No BL process, mailbox, timer, or death policy is
;; implemented here: canonical rt-pump-input delivers these events via rt-send.
;; Source selects the input sink and explicitly owns every resource lifetime.
(c-declare #<<c-end
#include <poll.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#define BL_NATIVE_WATCH_LIMIT 64
typedef struct bl_native_readiness {
  struct pollfd fds[BL_NATIVE_WATCH_LIMIT];
  unsigned count;
} bl_native_readiness;
static void *bl_native_readiness_new(void) {
  return calloc(1, sizeof(bl_native_readiness));
}
static int bl_native_readiness_add(void *ptr, int fd) {
  bl_native_readiness *r = ptr;
  if (fd < 0) return EINVAL;
  for (unsigned i = 0; i < r->count; ++i)
    if (r->fds[i].fd == fd) return EEXIST;
  if (r->count == BL_NATIVE_WATCH_LIMIT) return E2BIG;
  r->fds[r->count++] = (struct pollfd){fd, POLLIN, 0};
  return 0;
}
static int bl_native_readiness_remove(void *ptr, int fd) {
  bl_native_readiness *r = ptr;
  for (unsigned i = 0; i < r->count; ++i) {
    if (r->fds[i].fd == fd) {
      for (unsigned k = i + 1; k < r->count; ++k) r->fds[k - 1] = r->fds[k];
      --r->count;
      return 0;
    }
  }
  return ENOENT;
}
static int bl_native_readiness_wait(void *ptr, int timeout) {
  bl_native_readiness *r = ptr;
  long long deadline = timeout < 0 ? 0 : bl_native_now() + timeout;
  int remaining = timeout;
  for (;;) {
    int n = poll(r->fds, r->count, remaining);
    if (n >= 0) {
      for (unsigned i = 0; i < r->count; ++i)
        if (r->fds[i].revents & (POLLERR | POLLHUP | POLLNVAL)) return -EIO;
      return n;
    }
    if (errno != EINTR) return -errno;
    if (timeout >= 0) {
      long long rest = deadline - bl_native_now();
      if (rest <= 0) return 0;
      remaining = rest > INT_MAX ? INT_MAX : (int)rest;
    }
  }
}
static int bl_native_readiness_close(void *ptr) {
  bl_native_readiness *r = ptr;
  if (r->count) return EBUSY;
  free(r);
  return 0;
}
c-end
)
(define native-readiness-new (c-lambda () (pointer void) "bl_native_readiness_new"))
(define native-readiness-add (c-lambda ((pointer void) int) int "bl_native_readiness_add"))
(define native-readiness-remove (c-lambda ((pointer void) int) int "bl_native_readiness_remove"))
(define native-readiness-poll (c-lambda ((pointer void) int) int "bl_native_readiness_wait"))
(define native-readiness-close (c-lambda ((pointer void)) int "bl_native_readiness_close"))

(define native-readiness-reactor #f)
(define native-readiness-libraries '())
;; Each retained row is #(job library token state), state = new/watched/reported.
;; It owns the job capability until explicit Source close; C retains no Scheme
;; value and the worker only writes its result and its own completion eventfd.
(define native-readiness-jobs '())
(define native-readiness-queued 0)
(define native-readiness-timed-waits 0)
(define native-readiness-input-waits 0)
(define native-readiness-ready-wakes 0)
(define native-readiness-prior-input-size h-input-size)
(define native-readiness-library-path (getenv "BL_NATIVE_FFI_FIXTURE" #f))

(define (native-readiness-error message)
 (h-raise (string-append "native readiness: " message)))
(define (native-readiness-active!)
 (if (not native-readiness-reactor) (native-readiness-error "producer is not installed")))
(define (native-readiness-find-job job)
 (let loop ((rows native-readiness-jobs))
  (cond ((null? rows) (native-readiness-error "job is not owned by this producer"))
   ((eq? job (vector-ref (car rows) 0)) (car rows)) (else (loop (cdr rows))))))
(define (native-readiness-without value values)
 (cond ((null? values) '()) ((eq? value (car values)) (cdr values))
  (else (cons (car values) (native-readiness-without value (cdr values))))))
(define (native-readiness-token? value)
 (or (and (native-keyword? value) (<= (string-length (symbol->string value)) 4097))
     (and (h-is-int value) (<= 0 value) (< value (expt 2 64)))
     (and (string? value) (<= (string-length value) 4096))))
(define (native-readiness-watched-count)
 (let loop ((rows native-readiness-jobs) (count 0))
  (if (null? rows) count
   (loop (cdr rows) (+ count (if (eq? (vector-ref (car rows) 3) 'watched) 1 0))))))
(define (native-readiness-pump!)
 (native-readiness-active!)
 (for-each (lambda (row)
  (if (and (eq? (vector-ref row 3) 'watched) (native-ffi-ready? (vector-ref row 0)))
   (let* ((job (vector-ref row 0)) (token (vector-ref row 2))
          (event (bl-vec (list (bl-key "ffi-ready") token (native-ffi-result job)))))
    ;; Queue first: a full input queue must not silently discard completion.
    (native-input! event)
    (if (not (= 0 (native-readiness-remove native-readiness-reactor (native-ffi-fd job))))
     (native-readiness-error "completion eventfd was not registered"))
    (vector-set! row 3 'reported)
    (set! native-readiness-queued (+ native-readiness-queued 1))))) native-readiness-jobs)
 bl-nil)
(define (native-readiness-produce timeout)
 (native-readiness-active!)
 (if (not (or (not timeout) (and (h-is-int timeout) (>= timeout 0))))
  (native-badarg "readiness wait requires a nonnegative timeout or an infinite wait"))
 (native-readiness-pump!)
 (if (null? native-input-queue)
  (let ((watched (native-readiness-watched-count)))
   (if (and (= watched 0) (not timeout))
    (native-readiness-error "infinite input wait has no registered eventfd"))
   (if timeout
    (set! native-readiness-timed-waits (+ native-readiness-timed-waits 1))
    (set! native-readiness-input-waits (+ native-readiness-input-waits 1)))
   (let* ((chunk (if timeout (min timeout 2147483647) -1))
          (status (native-readiness-poll native-readiness-reactor chunk)))
    (if (< status 0) (native-readiness-error "poll failed"))
    (if (> status 0) (set! native-readiness-ready-wakes (+ native-readiness-ready-wakes 1)))
    ;; A chunk timeout simply returns to the canonical scheduler: it recomputes
    ;; the real remaining Source deadline, rather than sleeping past an input.
    (native-readiness-pump!)))) bl-nil)
(define (native-readiness-install!)
 (if (or native-readiness-reactor native-input-producer (pair? native-input-queue)
         (pair? native-readiness-jobs) (pair? native-readiness-libraries))
  (native-readiness-error "producer/input queue is already owned"))
 (if native-virtual-time? (native-readiness-error "real monotonic clock is required"))
 (let ((reactor (native-readiness-new)))
  (if (not reactor) (native-readiness-error "poll set allocation failed"))
  (set! native-readiness-reactor reactor))
 (set! native-input-producer native-readiness-produce) bl-nil)
(define (native-readiness-open-library! path)
 (native-readiness-active!)
 (let ((library (native-library-open path)))
  (set! native-readiness-libraries (cons library native-readiness-libraries)) library))
(define (native-readiness-submit! library symbol argument)
 (native-readiness-active!)
 (if (not (memq library native-readiness-libraries))
  (native-readiness-error "library is not owned by this producer"))
 (if (>= (length native-readiness-jobs) 64) (native-readiness-error "job bound exceeded"))
 (let ((job (native-ffi-submit library symbol argument)))
  (set! native-readiness-jobs (cons (vector job library #f 'new) native-readiness-jobs)) job))
(define (native-readiness-watch! job token)
 (native-readiness-active!)
 (if (not (native-readiness-token? token)) (native-readiness-error "completion token is not bounded scalar data"))
 (let ((row (native-readiness-find-job job)))
  (if (not (eq? (vector-ref row 3) 'new)) (native-readiness-error "job completion is one-shot"))
  (for-each (lambda (other)
   (if (and (eq? (vector-ref other 3) 'watched) (bl-equal? token (vector-ref other 2)))
    (native-readiness-error "completion token is already watched"))) native-readiness-jobs)
  (if (not (= 0 (native-readiness-add native-readiness-reactor (native-ffi-fd job))))
   (native-readiness-error "eventfd registration failed"))
  (vector-set! row 2 token) (vector-set! row 3 'watched)) bl-nil)
(define (native-readiness-close-job! job)
 (native-readiness-active!)
 (let ((row (native-readiness-find-job job)))
  (if (eq? (vector-ref row 3) 'watched)
   (native-readiness-error "consume completion before closing a watched job"))
  (native-ffi-close job)
  (set! native-readiness-jobs (native-readiness-without row native-readiness-jobs))) bl-nil)
(define (native-readiness-close-library! library)
 (native-readiness-active!)
 (if (not (memq library native-readiness-libraries))
  (native-readiness-error "library is not owned by this producer"))
 (native-library-close library)
 (set! native-readiness-libraries (native-readiness-without library native-readiness-libraries)) bl-nil)
(define (native-readiness-uninstall!)
 (native-readiness-active!)
 (if (or (pair? native-readiness-jobs) (pair? native-readiness-libraries) (pair? native-input-queue))
  (native-readiness-error "resources or queued completions remain"))
 (if (not (= 0 (native-readiness-close native-readiness-reactor)))
  (native-readiness-error "poll set still owns eventfds"))
 (set! native-readiness-reactor #f)
 (set! native-input-producer #f) bl-nil)
(define (native-readiness-stats)
 (bl-map (bl-key "queued") native-readiness-queued
  (bl-key "timed-waits") native-readiness-timed-waits
  (bl-key "input-waits") native-readiness-input-waits
  (bl-key "ready-wakes") native-readiness-ready-wakes
  (bl-key "jobs") (length native-readiness-jobs)
  (bl-key "libraries") (length native-readiness-libraries)))
(define (native-readiness-fixture-library)
 (if (not native-readiness-library-path) (native-readiness-error "fixture library path is not declared"))
 native-readiness-library-path)
;; Install the passive queue wrapper BEFORE emitted function/service tables.
;; C and Scheme call sites can retain this same procedure; Source install!
;; merely activates its reactor, rather than replacing a captured host leaf.
(set! h-input-size (native-mark-host-callable! (lambda ()
 (if native-readiness-reactor (native-readiness-pump!))
 (native-readiness-prior-input-size))))
(bl-register-callable! h-input-size 0)
(native-add-leaf! "native.readiness/install!/0" native-readiness-install!)
(native-add-leaf! "native.readiness/open-library!/1" native-readiness-open-library!)
(native-add-leaf! "native.readiness/submit!/3" native-readiness-submit!)
(native-add-leaf! "native.readiness/watch!/2" native-readiness-watch!)
(native-add-leaf! "native.readiness/close-job!/1" native-readiness-close-job!)
(native-add-leaf! "native.readiness/close-library!/1" native-readiness-close-library!)
(native-add-leaf! "native.readiness/uninstall!/0" native-readiness-uninstall!)
(native-add-leaf! "native.readiness/stats/0" native-readiness-stats)
(native-add-leaf! "native.readiness/fixture-library/0" native-readiness-fixture-library)
