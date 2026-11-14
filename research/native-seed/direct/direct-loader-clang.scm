;; Append after direct-loader.scm in the compiled host. The explicit Clang
;; configuration opts dynamic native.eval into the same public Gambit ABI as
;; qualify-scalar.py. Legacy configuration retains its existing implementation.
;; This file does not contain an evaluator or authored BL control.
(c-declare #<<c-end
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <errno.h>
#include <limits.h>

static long long blcc_millis(void) {
 struct timespec ts;
 if (clock_gettime(CLOCK_MONOTONIC,&ts)) return -1;
 return (long long)ts.tv_sec*1000+ts.tv_nsec/1000000;
}
static int blcc_public_abi(char *gsc,char *clang,char *include,char *buildscript) {
 const char *expected="DEFS_DYN=\" -D___SINGLE_HOST -D___TRUST_C_TCO -D___CAN_IMPORT_CLIB_DYNAMICALLY -D___CAN_IMPORT_SETJMP_DYNAMICALLY -D___DYNAMIC\"";
 char header[PATH_MAX],*line=NULL;size_t size=0;int count=0,valid=0;
 if (*gsc!='/' || *clang!='/' || *include!='/' || *buildscript!='/') return EINVAL;
 if (access(gsc,X_OK)||access(clang,X_OK)) return errno;
 if (snprintf(header,sizeof(header),"%s/gambit.h",include)>=(int)sizeof(header)) return ENAMETOOLONG;
 if (access(header,R_OK)) return errno;
 FILE *input=fopen(buildscript,"r");if (!input) return errno;
 while (getline(&line,&size,input)>=0) {
  size_t n=strlen(line);while(n&&(line[n-1]=='\n'||line[n-1]=='\r')) line[--n]=0;
  if (!strncmp(line,"DEFS_DYN=",9)) { count++;valid=!strcmp(line,expected); }
 }
 int status=ferror(input)?EIO:((count==1&&valid)?0:EINVAL);
 free(line);fclose(input);return status;
}
static int blcc_adapt_startup(char *rawpath,char *adaptedpath) {
 const char *prefix="#define ___LINKER_ID ";
 const char *from="#define ___LINKER_ID ___LNK_unit";
 const char *to="#define ___LINKER_ID ___LNK_unit_2e_o1";
 struct stat st;int input=open(rawpath,O_RDONLY);if(input<0)return errno;
 if(fstat(input,&st)){int e=errno;close(input);return e;}
 if(st.st_size<=0||(uintmax_t)st.st_size>=SIZE_MAX){close(input);return EFBIG;}
 size_t size=(size_t)st.st_size,have=0;char *text=malloc(size+1);
 if(!text){close(input);return ENOMEM;}
 while(have<size){ssize_t n=read(input,text+have,size-have);
  if(n<0&&errno==EINTR)continue;
  if(n<=0){int e=n<0?errno:EIO;close(input);free(text);return e;}have+=(size_t)n;}
 close(input);text[size]=0;
 char *line=text,*start=NULL,*end=NULL;int count=0,valid=0;
 while(line<text+size){char *next=memchr(line,'\n',(size_t)(text+size-line));
  char *finish=next?next:text+size;
  if((size_t)(finish-line)>=strlen(prefix)&&!memcmp(line,prefix,strlen(prefix))){
   count++;valid=(size_t)(finish-line)==strlen(from)&&!memcmp(line,from,strlen(from));
   start=line;end=finish;
  }
  line=next?next+1:text+size;
 }
 if(count!=1||!valid){free(text);return EINVAL;}
 int descriptor=open(adaptedpath,O_WRONLY|O_CREAT|O_EXCL,0600);
 if(descriptor<0){int e=errno;free(text);return e;}
 FILE *output=fdopen(descriptor,"wb");
 if(!output){int e=errno;close(descriptor);free(text);return e;}
 int status=0;
 if(fwrite(text,1,(size_t)(start-text),output)!=(size_t)(start-text)||
    fwrite(to,1,strlen(to),output)!=strlen(to)||
    fwrite(end,1,(size_t)(text+size-end),output)!=(size_t)(text+size-end))status=EIO;
 if(fclose(output)&&!status)status=errno;free(text);return status;
}
static int blcc_run(char **argv,int log,long long deadline) {
 dprintf(log,"native direct compile stage: %s\n",argv[0]);
 long long now=blcc_millis();if(now<0)return errno;if(now>=deadline)return 124;
 pid_t pid=fork();if(pid<0)return errno;
 if(!pid){
  if(setpgid(0,0))_exit(125);
  struct rlimit memory={2ULL*1024*1024*1024,2ULL*1024*1024*1024};
  rlim_t seconds=(rlim_t)((deadline-now)/1000+1);
  struct rlimit cpu={seconds,seconds+1};
  if(setrlimit(RLIMIT_AS,&memory)||setrlimit(RLIMIT_CPU,&cpu))_exit(125);
  if(dup2(log,STDOUT_FILENO)<0||dup2(log,STDERR_FILENO)<0)_exit(125);close(log);
  execv(argv[0],argv);_exit(127);
 }
 setpgid(pid,pid);
 for(;;){
  int status=0;pid_t done=waitpid(pid,&status,WNOHANG);
  if(done==pid)return WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status);
  if(done<0&&errno!=EINTR){int e=errno;kill(-pid,SIGKILL);while(waitpid(pid,&status,0)<0&&errno==EINTR){}return e;}
  long long current=blcc_millis();
  if(current<0||current>=deadline){kill(-pid,SIGKILL);while(waitpid(pid,&status,0)<0&&errno==EINTR){}return current<0?EIO:124;}
  struct timespec pause={0,10000000};nanosleep(&pause,NULL);
 }
}
static int blcc_compile(char *gsc,char *clang,char *include,char *buildscript,
                        char *source,char *output,char *directory,int timeout) {
 if(timeout<=0||timeout>120000)return EINVAL;
 int valid=blcc_public_abi(gsc,clang,include,buildscript);if(valid)return valid;
 char raw[PATH_MAX],adapted[PATH_MAX],logpath[PATH_MAX],inc[PATH_MAX+3],local[PATH_MAX+3];
 if(snprintf(raw,sizeof(raw),"%s/unit.c",directory)>=(int)sizeof(raw)||
    snprintf(adapted,sizeof(adapted),"%s/unit.dynamic.c",directory)>=(int)sizeof(adapted)||
    snprintf(logpath,sizeof(logpath),"%s/compile.log",directory)>=(int)sizeof(logpath)||
    snprintf(inc,sizeof(inc),"-I%s",include)>=(int)sizeof(inc)||
    snprintf(local,sizeof(local),"-I%s",directory)>=(int)sizeof(local))return ENAMETOOLONG;
 /* This exact basename is the public Gambit loader startup-symbol contract. */
 const char *base=strrchr(output,'/');base=base?base+1:output;
 if(strcmp(base,"unit.o1"))return EINVAL;
 int log=open(logpath,O_WRONLY|O_CREAT|O_EXCL,0600);if(log<0)return errno;
 long long now=blcc_millis();if(now<0){int e=errno;close(log);return e;}
 long long deadline=now+timeout;
 char *emit[]={gsc,"-c","-o",raw,source,NULL};
 int status=blcc_run(emit,log,deadline);
 if(!status)status=blcc_adapt_startup(raw,adapted);
 if(!status){
  char *compile[]={clang,"-O0","-fwrapv","-fno-strict-aliasing","-fno-trapping-math",
   "-fno-math-errno","-fPIC","-fno-common","-D___SINGLE_HOST","-D___TRUST_C_TCO",
   "-D___CAN_IMPORT_CLIB_DYNAMICALLY","-D___CAN_IMPORT_SETJMP_DYNAMICALLY","-D___DYNAMIC",
   inc,local,"-shared","-rdynamic",adapted,"-ldl","-lm","-o",output,NULL};
  status=blcc_run(compile,log,deadline);
 }
 if(status)dprintf(log,"native direct compile failed: status=%d\n",status);
 close(log);return status;
}
c-end
)
(define native-c-clang-validate
 (c-lambda (char-string char-string char-string char-string) int "blcc_public_abi"))
(define native-c-clang-compile
 (c-lambda (char-string char-string char-string char-string char-string char-string char-string int)
  int "blcc_compile"))
(define native-c-clang-toolchain #f)
(define native-c-legacy-configure! native-c-configure!)
(set! native-c-configure!
 (lambda (gsc header-source timeout)
  (let ((result (native-c-legacy-configure! gsc header-source timeout)))
   (set! native-c-clang-toolchain #f) result)))
(define native-c-legacy-compile-dynamic native-c-compile-dynamic)
(set! native-c-compile-dynamic
 (lambda (gsc source output directory timeout)
  (if native-c-clang-toolchain
   (native-c-clang-compile gsc (vector-ref native-c-clang-toolchain 0)
    (vector-ref native-c-clang-toolchain 1) (vector-ref native-c-clang-toolchain 2)
    source output directory timeout)
   (native-c-legacy-compile-dynamic gsc source output directory timeout))))
(define (native-c-configure-clang! gsc clang include buildscript header-source timeout)
 (if (or (not (string? gsc)) (not (string? clang)) (not (string? include))
         (not (string? buildscript)) (not (string? header-source))
         (not (integer? timeout)) (<= timeout 0) (> timeout 120000))
  (error "invalid direct C Clang compiler host configuration"))
 (let ((status (native-c-clang-validate gsc clang include buildscript)))
  (if (not (= status 0)) (error "pinned direct C Clang public ABI mismatch" status)))
 (native-c-configure! gsc header-source timeout)
 (set! native-c-clang-toolchain (vector clang include buildscript)) bl-nil)
