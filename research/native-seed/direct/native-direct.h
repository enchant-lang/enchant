/* Direct BL-ANF ABI, v1. C steps NEVER allocate or invoke Scheme/C callbacks.
 * Every Scheme value is owned by machine/unit/frame vectors, all roots passed
 * as the c-lambda scheme-object argument. No value is retained in C globals.
 * Allocation, language raises and scheduler suspension occur after C returns.
 * These macros are the pinned Gambit object's public generated-C ABI.
 */
#ifndef BL_NATIVE_DIRECT_H
#define BL_NATIVE_DIRECT_H
#include "gambit.h"
enum { BLC_SERVICE=1, BLC_CALL=2, BLC_RETURN=3, BLC_CLOSURE=4, BLC_TICK=5 };
static ___SCMOBJ blc_ref(___SCMOBJ x, int i) { return ___VECTORREF(x,___FIX(i)); }
static void blc_set(___SCMOBJ x, int i, ___SCMOBJ v) { ___VECTORSET(x,___FIX(i),v) }
#define BLC_UNIT(m) blc_ref(m,0)
#define BLC_FRAME(m) blc_ref(m,2)
#define BLC_REG(m,r) blc_ref(BLC_FRAME(m),r)
#define BLC_CONST(m,k) blc_ref(blc_ref(BLC_UNIT(m),1),k)
#define BLC_PUT(m,r,v) blc_set(BLC_FRAME(m),r,v)
#define BLC_PC(m,p) blc_set(m,1,___FIX(p))
#define BLC_TRUTHY(m,v) (!___FALSEP(v) && !___EQP(v,BLC_CONST(m,0)))
#define BLC_ACTION(m,a,d,n,p,t) do { blc_set(m,4,a); blc_set(m,5,___FIX(d)); \
 blc_set(m,6,___FIX(n)); blc_set(m,7,p); blc_set(m,8,(t)?___TRU:___FAL); } while(0)
#endif
