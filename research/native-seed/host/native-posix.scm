;; Native-only Gambit C FFI. Compile with -cc-options "-pthread" and
;; -ld-options "-pthread -ldl" (Linux). This unit must not be loaded by gsi.
;; Worker ABI is explicitly uint64_t (*)(uint64_t); no Scheme callbacks,
;; managed pointers, variadic calls, or structs may cross it. Each worker owns
;; a completion eventfd and retains its dlopen library until explicit release.
(c-declare #<<c-end
#define _GNU_SOURCE 1
#include <stdint.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <time.h>
#include <poll.h>
#include <unistd.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sys/eventfd.h>
typedef struct bl_native_library {
  void *handle;
  pthread_mutex_t lock;
  unsigned jobs;
} bl_native_library;
typedef struct bl_native_job {
  bl_native_library *library;
  uint64_t (*function)(uint64_t);
  uint64_t argument, result;
  int event;
  pthread_t thread;
  atomic_int done;
} bl_native_job;
static long long bl_native_now(void) {
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC, &t) != 0) return -errno;
  return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int bl_native_poll(int fd, int timeout) {
  struct pollfd p = {fd, POLLIN, 0};
  long long deadline = timeout < 0 ? 0 : bl_native_now() + timeout;
  int remaining = timeout;
  for (;;) {
    int n = poll(fd < 0 ? NULL : &p, fd < 0 ? 0 : 1, remaining);
    if (n >= 0) {
      if (n == 0) return 0;
      if (p.revents & (POLLERR|POLLHUP|POLLNVAL)) return -EIO;
      return (p.revents & POLLIN) ? 1 : 0;
    }
    if (errno != EINTR) return -errno;
    if (timeout >= 0) {
      long long rest = deadline - bl_native_now();
      if (rest <= 0) return 0;
      remaining = rest > INT_MAX ? INT_MAX : (int)rest;
    }
  }
}
static void *bl_native_library_open(char *path) {
  void *h = dlopen(path, RTLD_NOW|RTLD_LOCAL);
  if (!h) return NULL;
  bl_native_library *l = calloc(1, sizeof(*l));
  if (!l) { dlclose(h); return NULL; }
  int err = pthread_mutex_init(&l->lock, NULL);
  if (err) { free(l); dlclose(h); return NULL; }
  l->handle = h;
  return l;
}
static int bl_native_library_close(void *ptr) {
  bl_native_library *l = ptr;
  pthread_mutex_lock(&l->lock);
  if (l->jobs) { pthread_mutex_unlock(&l->lock); return EBUSY; }
  int status = dlclose(l->handle);
  pthread_mutex_unlock(&l->lock);
  if (status) return EIO;
  pthread_mutex_destroy(&l->lock); free(l); return 0;
}
static void *bl_native_worker(void *ptr) {
  bl_native_job *j = ptr;
  j->result = j->function(j->argument);
  atomic_store_explicit(&j->done, 1, memory_order_release);
  uint64_t one = 1;
  while (write(j->event, &one, sizeof(one)) < 0 && errno == EINTR) {}
  return NULL;
}
static void *bl_native_submit(void *ptr, char *symbol, unsigned long long arg) {
  bl_native_library *l = ptr;
  pthread_mutex_lock(&l->lock);
  dlerror();
  void *symbol_ptr = dlsym(l->handle, symbol);
  if (dlerror() != NULL) { pthread_mutex_unlock(&l->lock); return NULL; }
  bl_native_job *j = calloc(1, sizeof(*j));
  if (!j) { pthread_mutex_unlock(&l->lock); return NULL; }
  /* POSIX explicitly permits converting a dlsym result to a function pointer. */
  j->function = (uint64_t (*)(uint64_t))symbol_ptr;
  j->library = l; j->argument = arg;
  j->event = eventfd(0, EFD_CLOEXEC|EFD_NONBLOCK);
  if (j->event < 0) { free(j); pthread_mutex_unlock(&l->lock); return NULL; }
  atomic_init(&j->done, 0);
  int err = pthread_create(&j->thread, NULL, bl_native_worker, j);
  if (err) { close(j->event); free(j); pthread_mutex_unlock(&l->lock); return NULL; }
  l->jobs++;
  pthread_mutex_unlock(&l->lock); return j;
}
static int bl_native_job_fd(void *ptr) { return ((bl_native_job *)ptr)->event; }
static int bl_native_job_done(void *ptr) {
  return atomic_load_explicit(&((bl_native_job *)ptr)->done, memory_order_acquire);
}
static unsigned long long bl_native_job_result(void *ptr) { return ((bl_native_job *)ptr)->result; }
static int bl_native_job_close(void *ptr) {
  bl_native_job *j = ptr;
  if (!bl_native_job_done(j)) return EBUSY;
  int err = pthread_join(j->thread, NULL);
  if (err) return err;
  close(j->event);
  pthread_mutex_lock(&j->library->lock); j->library->jobs--; pthread_mutex_unlock(&j->library->lock);
  free(j); return 0;
}
c-end
)
(define native-posix-now (c-lambda () long-long "bl_native_now"))
(define native-posix-poll (c-lambda (int int) int "bl_native_poll"))
(define native-posix-library-open (c-lambda (char-string) (pointer void) "bl_native_library_open"))
(define native-posix-library-close (c-lambda ((pointer void)) int "bl_native_library_close"))
(define native-posix-submit (c-lambda ((pointer void) char-string unsigned-long-long) (pointer void) "bl_native_submit"))
(define native-posix-job-fd (c-lambda ((pointer void)) int "bl_native_job_fd"))
(define native-posix-job-done (c-lambda ((pointer void)) int "bl_native_job_done"))
(define native-posix-job-result (c-lambda ((pointer void)) unsigned-long-long "bl_native_job_result"))
(define native-posix-job-close (c-lambda ((pointer void)) int "bl_native_job_close"))
(define native-library-marker (list 'native-library-marker))
(define native-job-marker (list 'native-job-marker))
(define (native-capability-pointer x marker)
 (if (and (vector? x) (= (vector-length x) 3) (eq? (vector-ref x 0) marker) (vector-ref x 2))
  (vector-ref x 1) (native-badarg "closed or invalid native capability")))
(define (native-library-open path)
 (let ((p (native-posix-library-open path)))
  (if p (vector native-library-marker p #t) (h-raise "dlopen failed"))))
(define (native-library-close library)
 (let ((status (native-posix-library-close (native-capability-pointer library native-library-marker))))
  (if (= status 0) (begin (vector-set! library 2 #f) bl-nil) (h-raise "library still owns jobs or dlclose failed"))))
(define (native-ffi-submit library symbol argument)
 (if (not (and (h-is-int argument) (>= argument 0) (< argument (expt 2 64)))) (native-badarg "FFI uint64 argument"))
 (let ((p (native-posix-submit (native-capability-pointer library native-library-marker) symbol argument)))
  (if p (vector native-job-marker p #t) (h-raise "FFI submission failed"))))
(define (native-ffi-ready? job)
 (= (native-posix-job-done (native-capability-pointer job native-job-marker)) 1))
(define (native-ffi-fd job)
 (native-posix-job-fd (native-capability-pointer job native-job-marker)))
(define (native-ffi-result job)
 (if (native-ffi-ready? job) (native-posix-job-result (native-capability-pointer job native-job-marker))
  (h-raise "FFI result is not ready")))
(define (native-ffi-close job)
 (let ((status (native-posix-job-close (native-capability-pointer job native-job-marker))))
  (if (= status 0) (begin (vector-set! job 2 #f) bl-nil) (h-raise "FFI job is still running"))))
(define (native-wait-fd fd timeout-ms)
 (let ((result (native-posix-poll fd timeout-ms)))
  (if (< result 0) (h-raise (string-append "poll failed: " (number->string result))) (= result 1))))
(set! native-clock-reader (lambda ()
 (let ((ms (native-posix-now))) (if (< ms 0) (h-raise "clock_gettime failed") ms))))
(set! native-readiness-waiter (lambda (ms)
 (if (not (and (h-is-int ms) (>= ms 0))) (native-badarg "nonnegative integer wait required"))
 ;; Chunking avoids C int overflow without changing the requested deadline.
 (let ((deadline (+ (native-clock-reader) ms)))
  (let loop () (let ((remaining (- deadline (native-clock-reader))))
   (if (> remaining 0) (begin (native-wait-fd -1 (min remaining 2147483647)) (loop)))))) bl-nil))
(native-add-leaf! "native.host/clock-real!/0" native-use-real-time!)
(native-add-leaf! "native.host/library-open/1" native-library-open)
(native-add-leaf! "native.host/library-close/1" native-library-close)
(native-add-leaf! "native.host/ffi-submit/3" native-ffi-submit)
(native-add-leaf! "native.host/ffi-ready?/1" native-ffi-ready?)
(native-add-leaf! "native.host/ffi-fd/1" native-ffi-fd)
(native-add-leaf! "native.host/ffi-result/1" native-ffi-result)
(native-add-leaf! "native.host/ffi-close/1" native-ffi-close)
(native-add-leaf! "native.host/wait-fd/2" native-wait-fd)
