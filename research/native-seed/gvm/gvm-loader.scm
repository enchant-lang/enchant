;; The only external compiler boundary accepts validated, inert GVM DATA.
;; No Source/Scheme/ANF interpreter and no explicit C control stepper is loaded.
;; A whole host compilation is required for these finite POSIX IO bindings.
(c-declare #<<c-end
#define _GNU_SOURCE 1
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#include <errno.h>
#include <limits.h>
static char blgvm_directory[PATH_MAX];
static char *blgvm_new_directory(void) {
 snprintf(blgvm_directory,sizeof(blgvm_directory),"/tmp/beam-lisp-gvm-XXXXXX");
 return mkdtemp(blgvm_directory);
}
static long long blgvm_millis(void) {
 struct timespec ts;
 if (clock_gettime(CLOCK_MONOTONIC,&ts)) return -1;
 return (long long)ts.tv_sec*1000+ts.tv_nsec/1000000;
}
static int blgvm_build(char *python,char *driver,char *input,char *directory,char *name,int timeout) {
 char logpath[PATH_MAX];
 if (timeout<=0 || timeout>120000) return EINVAL;
 if (snprintf(logpath,sizeof(logpath),"%s/compile.log",directory)>=(int)sizeof(logpath)) return ENAMETOOLONG;
 int log=open(logpath,O_WRONLY|O_CREAT|O_EXCL,0600);
 if (log<0) return errno;
 long long start=blgvm_millis();
 if (start<0) { close(log);return EIO; }
 long long deadline=start+timeout;
 pid_t pid=fork();
 if (pid<0) { int e=errno;close(log);return e; }
 if (!pid) {
  if (setpgid(0,0)) _exit(125);
  struct rlimit memory={2ULL*1024*1024*1024,2ULL*1024*1024*1024};
  struct rlimit cpu={(rlim_t)(timeout/1000+1),(rlim_t)(timeout/1000+2)};
  if (setrlimit(RLIMIT_AS,&memory)||setrlimit(RLIMIT_CPU,&cpu)) _exit(125);
  if (dup2(log,STDOUT_FILENO)<0 || dup2(log,STDERR_FILENO)<0) _exit(125);
  close(log);
  char *args[]={python,driver,input,directory,"--name",name,"--route","c",NULL};
  execv(python,args);_exit(127);
 }
 close(log);setpgid(pid,pid);
 for (;;) {
  int status=0;pid_t done=waitpid(pid,&status,WNOHANG);
  if (done==pid) return WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status);
  if (done<0 && errno!=EINTR) { int e=errno;kill(-pid,SIGKILL);while(waitpid(pid,&status,0)<0&&errno==EINTR){};return e; }
  long long now=blgvm_millis();
  if (now<0 || now>=deadline) { kill(-pid,SIGKILL);while(waitpid(pid,&status,0)<0&&errno==EINTR){};return now<0?EIO:124; }
  struct timespec pause={0,10000000};nanosleep(&pause,NULL);
 }
}
c-end
)
(define native-gvm-new-directory (c-lambda () char-string "blgvm_new_directory"))
(define native-gvm-build-dynamic
 (c-lambda (char-string char-string char-string char-string char-string int) int "blgvm_build"))
(define (native-gvm-require-runtime-abi! abi)
 (if (not (and (exact-integer? abi) (= abi native-gvm-runtime-abi)))
  (error "native GVM runtime ABI mismatch" abi))
 (native-gvm-require-runtime! abi) abi)
(define native-gvm-toolchain #f)
(define native-gvm-counter 0)
(define native-gvm-loaded-artifacts '())
(define native-gvm-loaded-modules (bl-empty-map))
(define native-gvm-current-publisher (make-parameter #f))
(define (native-gvm-next-name)
 (set! native-gvm-counter (+ native-gvm-counter 1))
 (string-append "native_gvm_eval_" (number->string native-gvm-counter)))
(define (native-gvm-module-name? text)
 (and (string? text) (> (string-length text) 0) (<= (string-length text) 101)
  (let loop ((i 0))
   (if (= i (string-length text)) #t
    (let ((c (string-ref text i)))
     (and (or (and (char>=? c #\a) (char<=? c #\z))
              (and (char>=? c #\A) (char<=? c #\Z))
              (and (> i 0) (or (char=? c #\_) (char=? c #\-)
                 (and (char>=? c #\0) (char<=? c #\9)))))
      (loop (+ i 1))))))))
(define (native-gvm-validate-manifest! manifest)
 (native-gvm-require-runtime-abi! (bl-get manifest (bl-key "runtime-abi")))
 (if (not (and (bl-equal? (bl-get manifest (bl-key "schema")) "bl.native.gvm-emission")
               (eqv? (bl-get manifest (bl-key "version")) 1)
               (eq? (bl-get manifest (bl-key "program-control")) (bl-key "native-gvm"))
               (native-gvm-module-name? (bl-get manifest (bl-key "module")))))
  (error "GVM loader requires an actual native GVM emission manifest"))
 (for-each (lambda (key)
  (if (not (eq? (bl-get manifest (bl-key key)) #f))
   (error "GVM loader refuses interpreter or authored Scheme control" key)))
  '("authored-scheme" "source-interpreter" "anf-interpreter" "gvm-interpreter" "c-lambda-stepper"))
 (let ((owners (bl-get manifest (bl-key "owner-globals"))))
  (if (not (and (bl-tag? owners 'vec) (pair? (bl-items owners))
                (let loop ((xs (bl-items owners)))
                 (or (null? xs) (and (string? (car xs)) (loop (cdr xs)))))))
   (error "GVM manifest needs native owner globals")))
 manifest)
(define (native-gvm-publish-loaded! value)
 (let ((state (native-gvm-current-publisher)))
  (if (not (and (vector? state) (= (vector-length state) 5) (vector-ref state 0)))
   (error "GVM publication has no active module load"))
  (if (not (= (vector-ref state 1) 0)) (error "GVM module published twice"))
  (vector-set! state 1 1)
  (vector-set! state 2 value)) value)
(define (native-gvm-load-unit path manifest)
 (native-gvm-validate-manifest! manifest)
 (if (not (and (string? path) (file-exists? path)))
  (error "GVM native module is absent" path))
 (let ((module (bl-get manifest (bl-key "module")))
       (state (vector #t 0 bl-nil path manifest)))
  (if (native-map-has? native-gvm-loaded-modules module)
   (error "GVM native module name was already loaded" module))
  (set! native-gvm-loaded-modules (bl-assoc native-gvm-loaded-modules module path))
  (with-exception-catcher
   (lambda (failure) (vector-set! state 0 #f) (raise failure))
   (lambda ()
    (parameterize ((native-gvm-current-publisher state)) (load path))
    (vector-set! state 0 #f)
    (if (not (= (vector-ref state 1) 1)) (error "GVM module did not publish its result" module))
    (set! native-gvm-loaded-artifacts (cons state native-gvm-loaded-artifacts))
    (vector-ref state 2)))))
(define (native-gvm-configure! python driver expected-inputs timeout)
 (if (not (and (string? python) (string? driver) (native-list? expected-inputs)
               (exact-integer? timeout) (> timeout 0) (<= timeout 120000)))
  (error "invalid GVM compiler host configuration"))
 (for-each (lambda (row)
  (if (not (and (pair? row) (string? (car row)) (string? (cdr row))
                (string=? (native-gvm-file-sha256 (car row)) (cdr row))))
   (error "GVM backend input changed" row))) expected-inputs)
 (set! native-gvm-toolchain (vector python driver expected-inputs timeout)) bl-nil)
(define (native-gvm-eval-unit emitted)
 (if (not native-gvm-toolchain) (error "native GVM dynamic backend is not configured"))
 (let* ((manifest (native-gvm-validate-manifest! (bl-get emitted (bl-key "manifest"))))
        (source (bl-get emitted (bl-key "data-source")))
        (name (bl-get manifest (bl-key "module"))))
  (if (not (string? source)) (error "GVM loader requires DATA source"))
  ;; Recheck the finite pinned backend custody inputs before external execution.
  (for-each (lambda (row)
   (if (not (string=? (native-gvm-file-sha256 (car row)) (cdr row)))
    (error "GVM backend input changed since configuration" (car row))))
   (vector-ref native-gvm-toolchain 2))
  (let* ((directory (native-gvm-new-directory))
         (_ (if (not directory) (error "GVM private directory creation failed")))
         (input (string-append directory "/module.gvm-data"))
         (output (string-append directory "/" name ".o1")))
   (native-write-file input source)
   (let ((status (native-gvm-build-dynamic (vector-ref native-gvm-toolchain 0)
                  (vector-ref native-gvm-toolchain 1) input directory name
                  (vector-ref native-gvm-toolchain 3))))
    (if (not (= status 0))
     (error "GVM native module compilation failed" status directory
       (native-read-file (string-append directory "/compile.log")))))
   (let ((value (native-gvm-load-unit output manifest)))
    (set! native-gvm-loaded-artifacts
     (cons (vector directory emitted output value) native-gvm-loaded-artifacts))
    value))))
(native-add-leaf! "host/native-gvm-next-name/0" native-gvm-next-name)
(native-add-leaf! "host/eval-gvm-unit/1" native-gvm-eval-unit)
