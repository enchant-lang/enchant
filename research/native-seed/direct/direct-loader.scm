;; Native compiler's dynamic C-unit loader. Compile this host unit once with
;; gsc; gsi cannot evaluate c-declare/c-lambda. Configure using the immutable
;; toolchain pin and exact native-direct.h source before admitting compiler work.
;; Dynamic children use argv, private directories, CPU/address-space limits and
;; a monotonic wall deadline. No shell command is built from source text.
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
static char blc_directory[PATH_MAX];
static char *blc_new_directory(void) {
 snprintf(blc_directory,sizeof(blc_directory),"/tmp/beam-lisp-direct-XXXXXX");
 return mkdtemp(blc_directory);
}
static long long blc_millis(void) {
 struct timespec ts;
 if (clock_gettime(CLOCK_MONOTONIC,&ts)) return -1;
 return (long long)ts.tv_sec*1000+ts.tv_nsec/1000000;
}
static int blc_compile_dynamic(char *gsc,char *source,char *output,char *directory,int timeout) {
 char include[PATH_MAX+3],logpath[PATH_MAX];
 if (timeout<=0 || timeout>240000) return EINVAL;
 if (snprintf(include,sizeof(include),"-I%s",directory)>=(int)sizeof(include)) return ENAMETOOLONG;
 if (snprintf(logpath,sizeof(logpath),"%s/compile.log",directory)>=(int)sizeof(logpath)) return ENAMETOOLONG;
 int log=open(logpath,O_WRONLY|O_CREAT|O_EXCL,0600);
 if (log<0) return errno;
 long long deadline=blc_millis()+timeout;
 pid_t pid=fork();
 if (pid<0) { int e=errno;close(log);return e; }
 if (!pid) {
  setpgid(0,0);
  struct rlimit memory={8ULL*1024*1024*1024,8ULL*1024*1024*1024};
  struct rlimit cpu={(rlim_t)(timeout/1000+1),(rlim_t)(timeout/1000+2)};
  if (setrlimit(RLIMIT_AS,&memory)||setrlimit(RLIMIT_CPU,&cpu)) _exit(125);
  dup2(log,STDOUT_FILENO);dup2(log,STDERR_FILENO);close(log);
  char *args[]={gsc,"-dynamic","-o",output,"-cc-options",include,source,NULL};
  execv(gsc,args);_exit(127);
 }
 close(log);setpgid(pid,pid);
 for (;;) {
  int status=0;pid_t done=waitpid(pid,&status,WNOHANG);
  if (done==pid) return WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status);
  if (done<0 && errno!=EINTR) return errno;
  if (blc_millis()>=deadline) { kill(-pid,SIGKILL);while(waitpid(pid,&status,0)<0&&errno==EINTR){};return 124; }
  struct timespec pause={0,10000000};nanosleep(&pause,NULL);
 }
}
c-end
)
(define native-c-new-directory (c-lambda () char-string "blc_new_directory"))
(define native-c-compile-dynamic
 (c-lambda (char-string char-string char-string char-string int) int "blc_compile_dynamic"))
(define native-c-toolchain #f)
(define native-c-loaded-artifacts '())
(define native-c-current-publisher (make-parameter #f))
(define (native-c-publish-loaded! value)
 (let ((publish (native-c-current-publisher))) (if publish (publish value))) value)
;; This is a fixed C-header admission stamp, not a Source parser. The emitted
;; C preprocessor guard independently checks the actual included ABI value.
(define (native-c-header-action-abi2? source)
 (and (string? source)
  (let ((size (string-length source))
        (prefix "#define BL_NATIVE_DIRECT_ABI ")
        (expected "#define BL_NATIVE_DIRECT_ABI 2"))
   (let loop ((start 0) (offset 0) (found 0))
    (if (or (= offset size) (char=? (string-ref source offset) #\newline))
     (let* ((line (substring source start offset))
            (definition? (and (>= (string-length line) (string-length prefix))
              (string=? prefix (substring line 0 (string-length prefix)))))
            (next-found (if definition? (+ found 1) found)))
      (and (or (not definition?) (string=? line expected))
       (if (= offset size) (= next-found 1)
        (loop (+ offset 1) (+ offset 1) next-found))))
     (loop start (+ offset 1) found))))))

(define (native-c-configure! gsc header-source timeout)
 (native-c-require-action-abi! 2)
 (if (not (native-c-header-action-abi2? header-source))
  (error "direct C compiler header requires action ABI2"))
 (if (or (not (string? gsc)) (not (string? header-source))
         (not (integer? timeout)) (<= timeout 0) (> timeout 240000))
  (error "invalid direct C compiler host configuration"))
 (set! native-c-toolchain (vector gsc header-source timeout)) bl-nil)
(define (native-c-eval-unit emitted)
 (if (not native-c-toolchain) (error "direct C dynamic compiler host is not configured"))
 (let* ((source (bl-get emitted (bl-key "wrapper-source")))
        (manifest (bl-get emitted (bl-key "manifest")))
        (_ (native-c-require-action-abi! (bl-get manifest (bl-key "action-abi"))))
        (directory (native-c-new-directory))
        (input (and directory (string-append directory "/unit.scm")))
        (output (and directory (string-append directory "/unit.o1")))
        (seen? #f) (value bl-nil))
  (if (or (not (string? source)) (not directory)
          (not (bl-equal? (bl-get manifest (bl-key "schema")) "bl.native.direct-c-unit"))
          (not (eqv? (bl-get manifest (bl-key "version")) 1)))
   (error "direct C loader requires a concrete emitted unit"))
  (native-write-file input source)
  (native-write-file (string-append directory "/native-direct.h") (vector-ref native-c-toolchain 1))
  (let ((status (native-c-compile-dynamic (vector-ref native-c-toolchain 0) input output
                  directory (vector-ref native-c-toolchain 2))))
   (if (not (= status 0))
    (error "direct C unit compilation failed" status
      (native-read-file (string-append directory "/compile.log")))))
  (parameterize ((native-c-current-publisher
                  (lambda (result) (if seen? (error "direct C unit published twice"))
                   (set! seen? #t) (set! value result))))
   (load output))
  (if (not seen?) (error "direct C unit did not publish its result"))
  (set! native-c-loaded-artifacts (cons (vector directory emitted) native-c-loaded-artifacts))
  value))
(native-add-leaf! "host/eval-c-unit/1" native-c-eval-unit)
(define native-c-backend (bl-key "scheme"))
(native-add-leaf! "host/native-backend/0" (lambda () native-c-backend))
(native-add-leaf! "host/set-native-backend/1" (lambda (backend)
 (if (not (or (eq? backend (bl-key "scheme")) (eq? backend (bl-key "c"))))
  (error "unknown native compiler backend" backend))
 (set! native-c-backend backend) backend))
