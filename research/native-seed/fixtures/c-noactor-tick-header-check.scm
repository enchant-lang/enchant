;; Real C ABI probe, compiled into the EXISTING native POSIX fixture ELF.
;; This checks optional transport/header boundaries, not a Source program.
(c-declare #<<c-end
#include "native-direct.h"
static int native_tick_header_probe(___SCMOBJ machine) {
 return BLC_SKIP_NOACTOR_TICK(machine);
}
static int native_tick_boundary_probe(___SCMOBJ m) {
 ___WORD blc_pc=___INT(blc_ref(m,1));
 for (;;) {
  switch ((int)blc_pc) {
   case 41:
    blc_set(m,11,___FAL);
    BLC_ACTION(m,___FIX(0),0,7,___NUL,0);
    if (BLC_SKIP_NOACTOR_TICK(m)) { BLC_PC(m,7); continue; }
    BLC_YIELD(m,BLC_TICK);
   case 7: BLC_YIELD(m,BLC_RETURN);
   default: BLC_YIELD(m,-1);
  }
 }
}
c-end
)
(define native-tick-header-probe (c-lambda (scheme-object) int "native_tick_header_probe"))
(define native-tick-boundary-probe (c-lambda (scheme-object) int "native_tick_boundary_probe"))
(define native-tick-header-checks 0)
(define (tick-header-check label actual expected)
 (if (not (equal? actual expected)) (error "optional tick C boundary" label actual expected))
 (set! native-tick-header-checks (+ native-tick-header-checks 1)))
(define (tick-header-machine extension)
 (let ((machine (make-vector 15 #f)))
  (vector-set! machine 1 41) (vector-set! machine 14 extension) machine))
(tick-header-check 'legacy14 (native-tick-header-probe (make-vector 14 #f)) 0)
(tick-header-check 'unknown16 (native-tick-header-probe (make-vector 16 #f)) 0)
(tick-header-check 'nonvector-extension (native-tick-header-probe (tick-header-machine 42)) 0)
(tick-header-check 'short-extension (native-tick-header-probe (tick-header-machine '#(1 1 0 #()))) 0)
(tick-header-check 'unknown-version (native-tick-header-probe (tick-header-machine '#(2 1 0 #() 0))) 0)
(tick-header-check 'disabled-state (native-tick-header-probe (tick-header-machine '#(1 0 0 #() 0))) 0)
(let* ((ledger (vector 'ledger)) (extension (vector 1 1 37 ledger 13))
       (machine (tick-header-machine extension)))
 (tick-header-check 'eligible-state (native-tick-header-probe machine) 1)
 (tick-header-check 'skip-marked (vector-ref extension 1) 2)
 (tick-header-check 'second-skip-refused (native-tick-header-probe machine) 0)
 (tick-header-check 'independent-fields-retained
  (and (= (vector-ref extension 2) 37) (eq? (vector-ref extension 3) ledger)
       (= (vector-ref extension 4) 13)) #t))
(tick-header-check 'boolean-is-not-ready (native-tick-header-probe (tick-header-machine '#(1 #t 0 #() 0))) 0)
(let* ((extension (vector 1 1 0 '#() 0 'future)) (machine (tick-header-machine extension)))
 (tick-header-check 'append-compatible-extension
  (and (= (native-tick-header-probe machine) 1) (eq? (vector-ref extension 5) 'future)) #t))
(let ((legacy (make-vector 14 #f)))
 (vector-set! legacy 1 41)
 (tick-header-check 'legacy-boundary-action (native-tick-boundary-probe legacy) 5)
 (tick-header-check 'legacy-local-PC-synchronized (vector-ref legacy 1) 41))
(let ((disabled (tick-header-machine (vector 1 0 0 '#() 0))))
 (tick-header-check 'disabled-boundary-action (native-tick-boundary-probe disabled) 5)
 (tick-header-check 'disabled-local-PC-synchronized (vector-ref disabled 1) 41))
(let* ((extension (vector 1 1 0 '#() 0)) (machine (tick-header-machine extension)))
 (tick-header-check 'fast-boundary-continues (native-tick-boundary-probe machine) 3)
 (tick-header-check 'fast-local-PC-advances (vector-ref machine 1) 7)
 (tick-header-check 'tick-transport-writes-retained
  (and (= (vector-ref machine 4) 0) (= (vector-ref machine 5) 0)
       (= (vector-ref machine 6) 7) (null? (vector-ref machine 7))
       (eq? (vector-ref machine 8) #f) (eq? (vector-ref machine 11) #f)) #t)
 (tick-header-check 'fast-boundary-marks-one-skip (vector-ref extension 1) 2))
;; The real C step is captured once at unit4. Replace only unit0 with
;; an actual Scheme profiling wrapper that mutates h-tick, then forwards into
;; that SAME C function. The owned-step fence must deopt before the wrapper.
(let* ((saved-tick h-tick) (saved-enabled native-c-noactor-tick-enabled?)
       (before native-c-noactor-ticks-elided) (calls 0) (ticks 0) (modes '())
       (unit (vector native-tick-boundary-probe '#() '#() 0 native-tick-boundary-probe))
       (tick (lambda () (set! ticks (+ ticks 1)) (saved-tick)))
       (function (native-c-new-closure unit
        (list 41 2 '() (bl-map (bl-key "arity") 0 (bl-key "native-control") #f)) '()))
       (answer #f))
 (set! native-c-noactor-tick-enabled? #t)
 (vector-set! unit 0 (lambda (machine)
  (set! calls (+ calls 1))
  (set! modes (cons (vector-ref (vector-ref machine 14) 1) modes))
  (set! h-tick tick)
  (native-tick-boundary-probe machine)))
 (set! answer (native-c-invoke function '()))
 (set! h-tick saved-tick) (set! native-c-noactor-tick-enabled? saved-enabled)
 (tick-header-check 'wrapped-real-C-was-called calls 2)
 (tick-header-check 'wrapped-real-C-never-armed modes '(0 0))
 (tick-header-check 'wrapped-real-C-observes-new-tick ticks 1)
 (tick-header-check 'wrapped-real-C-return-value answer 0)
 (tick-header-check 'wrapped-real-C-no-elision native-c-noactor-ticks-elided before))
(if (not (= native-tick-header-checks 25)) (error "optional C tick fixture count" native-tick-header-checks))
(display "NATIVE_C_NOACTOR_TICK_HEADER_PASS 25") (newline)
