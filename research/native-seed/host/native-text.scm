;; Native PCRE2-10.48 adapter. Runtime library is an immutable pinned Nix input;
;; the ABI declarations come from PCRE2's public 10.48 header. No vendored engine.
;; Sources: https://github.com/PCRE2Project/pcre2/blob/pcre2-10.48/src/pcre2.h.generic
(c-declare #<<c-end
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#define BL_PCRE_PATH "/nix/store/6vqahj875znq0wlsy1bg926yki3d5m4r-pcre2-10.48/lib/libpcre2-8.so"
typedef struct bl_text_result { int status; size_t rows, width, capacity; size_t *offsets; } bl_text_result;
static void *bl_text_library = NULL;
static void *(*bl_pc_compile)(const uint8_t*,size_t,uint32_t,int*,size_t*,void*);
static void (*bl_pc_code_free)(void*);
static void *(*bl_pc_data_new)(const void*,void*);
static void (*bl_pc_data_free)(void*);
static int (*bl_pc_match)(const void*,const uint8_t*,size_t,size_t,uint32_t,void*,void*);
static uint32_t (*bl_pc_vector_count)(void*);
static size_t *(*bl_pc_vector)(void*);
static void *(*bl_pc_context_new)(void*);
static void (*bl_pc_context_free)(void*);
static int (*bl_pc_match_limit)(void*,uint32_t);
static int bl_text_init(void) {
 if (bl_text_library) return 1;
 void *library = dlopen(BL_PCRE_PATH, RTLD_NOW|RTLD_LOCAL);
 if (!library) return 0;
 #define BL_PC_LOAD(slot,name) do { *(void **)(&slot) = dlsym(library,name); if (!slot) { dlclose(library); return 0; } } while(0)
 BL_PC_LOAD(bl_pc_compile,"pcre2_compile_8"); BL_PC_LOAD(bl_pc_code_free,"pcre2_code_free_8");
 BL_PC_LOAD(bl_pc_data_new,"pcre2_match_data_create_from_pattern_8"); BL_PC_LOAD(bl_pc_data_free,"pcre2_match_data_free_8");
 BL_PC_LOAD(bl_pc_match,"pcre2_match_8"); BL_PC_LOAD(bl_pc_vector_count,"pcre2_get_ovector_count_8"); BL_PC_LOAD(bl_pc_vector,"pcre2_get_ovector_pointer_8");
 BL_PC_LOAD(bl_pc_context_new,"pcre2_match_context_create_8"); BL_PC_LOAD(bl_pc_context_free,"pcre2_match_context_free_8");
 BL_PC_LOAD(bl_pc_match_limit,"pcre2_set_match_limit_8");
 #undef BL_PC_LOAD
 bl_text_library = library; return 1;
}
static void *bl_text_scan(char *pattern, unsigned long long plen, char *text, unsigned long long length, int global) {
 bl_text_result *r = calloc(1,sizeof(*r)); if (!r) return NULL;
 if (!bl_text_init()) { r->status = -10000; return r; }
 int error = 0; size_t error_offset = 0;
 /* UTF and UCP: scalar-valid UTF8, Unicode properties, and Unicode \X. */
 void *code = bl_pc_compile((const uint8_t*)pattern,(size_t)plen,0x000a0000u,&error,&error_offset,NULL);
 if (!code) { r->status = error; return r; }
 void *data = bl_pc_data_new(code,NULL), *context = bl_pc_context_new(NULL);
 if (!data || !context) { if(data)bl_pc_data_free(data); if(context)bl_pc_context_free(context); bl_pc_code_free(code); free(r); return NULL; }
 bl_pc_match_limit(context,10000000);
 r->width = (size_t)bl_pc_vector_count(data);
 size_t offset = 0; int empty = 0;
 for (;;) {
  int rc = bl_pc_match(code,(const uint8_t*)text,(size_t)length,offset,empty ? 0x80000008u : 0u,data,context);
  if (rc == -1) {
   if (empty && offset < (size_t)length) { offset++; while(offset < (size_t)length && (((uint8_t)text[offset] & 0xc0u) == 0x80u))offset++; empty=0; continue; }
   break;
  }
  if (rc < 0) { r->status = rc; break; }
  if (r->rows >= 1048576) { r->status = -10001; break; }
  if (r->rows == r->capacity) {
   size_t cap = r->capacity ? r->capacity*2 : 16;
   if (r->width > SIZE_MAX/(cap*2*sizeof(size_t))) { r->status=-10002; break; }
   size_t *next = realloc(r->offsets,cap*r->width*2*sizeof(size_t));
   if (!next) { r->status=-10002; break; } r->offsets=next; r->capacity=cap;
  }
  size_t *v = bl_pc_vector(data);
  memcpy(r->offsets+r->rows*r->width*2,v,r->width*2*sizeof(size_t)); r->rows++;
  if (!global) break;
  offset = v[1]; empty = v[0] == v[1];
  if (offset > length) { r->status=-10003; break; }
 }
 bl_pc_context_free(context); bl_pc_data_free(data); bl_pc_code_free(code); return r;
}
static int bl_text_status(void *p) { return ((bl_text_result*)p)->status; }
static unsigned long long bl_text_rows(void *p) { return ((bl_text_result*)p)->rows; }
static unsigned long long bl_text_width(void *p) { return ((bl_text_result*)p)->width; }
static long long bl_text_offset(void *p, unsigned long long row, unsigned long long group, int end) {
 bl_text_result *r=p;
 if (row>=r->rows || group>=r->width) return -1;
 size_t offset=r->offsets[(row*r->width+group)*2+(end ? 1 : 0)];
 return offset == SIZE_MAX ? -1 : (long long)offset;
}
static void bl_text_release(void *p) { bl_text_result *r=p; free(r->offsets); free(r); }
c-end
)
(define native-text-scan (c-lambda (UTF-8-string unsigned-long-long UTF-8-string unsigned-long-long int) (pointer void) "bl_text_scan"))
(define native-text-status (c-lambda ((pointer void)) int "bl_text_status"))
(define native-text-rows (c-lambda ((pointer void)) unsigned-long-long "bl_text_rows"))
(define native-text-width (c-lambda ((pointer void)) unsigned-long-long "bl_text_width"))
(define native-text-offset (c-lambda ((pointer void) unsigned-long-long unsigned-long-long int) long-long "bl_text_offset"))
(define native-text-release (c-lambda ((pointer void)) void "bl_text_release"))
(define native-regex-marker (list 'native-regex-marker))
(define (native-regex? x) (and (vector? x) (= (vector-length x) 2) (eq? (vector-ref x 0) native-regex-marker)))
(define (native-with-matches pattern text global? body)
 (let ((result (native-text-scan pattern (length (native-utf8-bytes pattern)) text (length (native-utf8-bytes text)) (if global? 1 0))))
  (if (not result) (h-raise "native PCRE2 allocation failed"))
  (dynamic-wind (lambda () #f)
   (lambda () (if (not (= (native-text-status result) 0))
    (h-raise (string-append "native PCRE2 error: " (number->string (native-text-status result)))) (body result)))
   (lambda () (native-text-release result)))))
(define (native-regex-compile pattern)
 (native-with-matches pattern "" #f (lambda (result) #f)) (vector native-regex-marker pattern))
(define (native-byte-slice bytes a b)
 (let loop ((i (- b 1)) (out '())) (if (< i a) (native-utf8-string out) (loop (- i 1) (cons (vector-ref bytes i) out)))))
(define (native-regex-captures result row bytes)
 (let loop ((i (- (native-text-width result) 1)) (out '()))
  (if (< i 0) out (let ((a (native-text-offset result row i 0)) (b (native-text-offset result row i 1)))
   (loop (- i 1) (cons (if (< a 0) "" (native-byte-slice bytes a b)) out))))))
(define (native-regex-run regex text)
 (native-with-matches (vector-ref regex 1) text #f
  (lambda (result) (if (= (native-text-rows result) 0) bl-nil
   (native-regex-captures result 0 (list->vector (native-utf8-bytes text)))))))
(define (native-regex-scan regex text)
 (native-with-matches (vector-ref regex 1) text #t
  (lambda (result) (let ((bytes (list->vector (native-utf8-bytes text))))
   (let loop ((row (- (native-text-rows result) 1)) (out '()))
    (if (< row 0) out (loop (- row 1) (cons (native-regex-captures result row bytes) out))))))))
(define (native-regex-expand replacement captures)
 (let loop ((xs (string->list replacement)) (out '()))
  (cond ((null? xs) (native-join "" (reverse out)))
   ((and (char=? (car xs) #\\) (pair? (cdr xs)))
    (let ((ch (cadr xs)))
     (if (and (char>=? ch #\0) (char<=? ch #\9))
      (let digits ((p (cdr xs)) (n 0))
       (if (and (pair? p) (char>=? (car p) #\0) (char<=? (car p) #\9))
        (digits (cdr p) (+ (* n 10) (- (char->integer (car p)) 48)))
        (loop p (cons (if (< n (length captures)) (list-ref captures n) "") out))))
      (loop (cddr xs) (cons (string ch) out)))))
   (else (loop (cdr xs) (cons (string (car xs)) out))))))
(define (native-regex-replace regex text replacement . options)
 (if (not (string? replacement)) (native-badarg "regex callback replacement requires a declared callable ABI"))
 (let* ((opts (if (null? options) '() (car options)))
        (global? (let loop ((ps opts)) (cond ((null? ps) #t)
          ((eq? (bl-nth (car ps) 0) (bl-key "global")) (bl-truthy (bl-nth (car ps) 1))) (else (loop (cdr ps)))))))
  (native-with-matches (vector-ref regex 1) text global?
   (lambda (result) (let ((bytes (list->vector (native-utf8-bytes text))))
    (let loop ((row 0) (offset 0) (out '()))
     (if (= row (native-text-rows result)) (native-join "" (reverse (cons (native-byte-slice bytes offset (vector-length bytes)) out)))
      (let ((a (native-text-offset result row 0 0)) (b (native-text-offset result row 0 1)))
       (loop (+ row 1) b (cons (native-regex-expand replacement (native-regex-captures result row bytes))
                          (cons (native-byte-slice bytes offset a) out)))))))))))
(set! native-graphemes (lambda (text)
 (native-with-matches "\\X" text #t (lambda (result)
  (let ((bytes (list->vector (native-utf8-bytes text))))
   (let loop ((row (- (native-text-rows result) 1)) (out '()))
    (if (< row 0) out (loop (- row 1)
     (cons (native-byte-slice bytes (native-text-offset result row 0 0) (native-text-offset result row 0 1)) out)))))))))
(native-add-leaf! "Elixir.Regex/compile!/1" native-regex-compile)
(native-add-leaf! "Elixir.Regex/regex?/1" native-regex?)
(native-add-leaf! "Elixir.Regex/run/2" native-regex-run)
(native-add-leaf! "Elixir.Regex/scan/2" native-regex-scan)
(native-add-leaf! "Elixir.Regex/replace/3" native-regex-replace)
(native-add-leaf! "Elixir.Regex/replace/4" native-regex-replace)
;; Binary String.replace also admits a Regex as Elixir does. Keep raw binary
;; operations pure; only regex branches enter this native engine.
(define native-binary-string-replace native-string-replace)
(set! native-string-replace (lambda (text pattern replacement options)
 (if (native-regex? pattern) (native-regex-replace pattern text replacement options)
  (native-binary-string-replace text pattern replacement options))))
(define native-binary-string-split native-string-split)
(define (native-regex-split text regex options)
 (let ((trim? (let loop ((ps options)) (cond ((null? ps) #f)
        ((eq? (bl-nth (car ps) 0) (bl-key "trim")) (bl-truthy (bl-nth (car ps) 1))) (else (loop (cdr ps))))))
       (parts (let loop ((ps options)) (cond ((null? ps) #f)
        ((eq? (bl-nth (car ps) 0) (bl-key "parts")) (bl-nth (car ps) 1)) (else (loop (cdr ps)))))))
  (native-with-matches (vector-ref regex 1) text #t (lambda (result)
   (let* ((bytes (list->vector (native-utf8-bytes text)))
          (xs (let loop ((row 0) (offset 0) (count 1) (out '()))
           (if (or (= row (native-text-rows result)) (and parts (>= count parts)))
            (reverse (cons (native-byte-slice bytes offset (vector-length bytes)) out))
            (loop (+ row 1) (native-text-offset result row 0 1) (+ count 1)
             (cons (native-byte-slice bytes offset (native-text-offset result row 0 0)) out))))))
    (if trim? (let loop ((xs xs) (out '())) (if (null? xs) (reverse out)
      (loop (cdr xs) (if (= (string-length (car xs)) 0) out (cons (car xs) out))))) xs))))))
(set! native-string-split (lambda (text pattern options)
 (if (native-regex? pattern) (native-regex-split text pattern options)
  (native-binary-string-split text pattern options))))
(define (native-string-to-float chars)
 (let* ((text (list->string (map integer->char chars)))
        (captures (native-regex-run (native-regex-compile "\\A[+-]?[0-9]+\\.[0-9]+(?:[eE][+-]?[0-9]+)?") text)))
  (if (bl-is-nil captures) (bl-tuple (list (bl-key "error") (bl-key "no_float")))
   (let* ((prefix (car captures)) (number (string->number prefix)))
    (bl-tuple (list (bl-float number) (native-drop chars (string-length prefix))))))))
(native-add-leaf! "string/to_float/1" native-string-to-float)
