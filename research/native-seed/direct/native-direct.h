/* Direct BL-ANF ABI, v2. C steps NEVER allocate or invoke Scheme/C callbacks.
 * Every Scheme value is owned by machine/unit/frame vectors, all roots passed
 * as the c-lambda scheme-object argument. No value is retained in C globals.
 * Allocation, language raises and scheduler suspension occur after C returns.
 * These macros are the pinned Gambit object's public generated-C ABI.
 */
#ifndef BL_NATIVE_DIRECT_H
#define BL_NATIVE_DIRECT_H
#include "gambit.h"
#define BL_NATIVE_DIRECT_ABI 2
enum { BLC_SERVICE=1, BLC_CALL=2, BLC_RETURN=3, BLC_CLOSURE=4, BLC_TICK=5, BLC_CALL_SLOTS=6 };
static ___SCMOBJ blc_ref(___SCMOBJ x, int i) { return ___VECTORREF(x,___FIX(i)); }
static void blc_set(___SCMOBJ x, int i, ___SCMOBJ v) { ___VECTORSET(x,___FIX(i),v); }
/* An OPTIONAL extension: a legacy 14-slot ABI2 machine always takes the old
 * tick path. One skip is permitted per returned C step; 2 means observed skip.
 * C still makes no allocation, callback or safepoint while this state is live.
 */
static int blc_skip_noactor_tick(___SCMOBJ m) {
 ___SCMOBJ ___temp;
 if (___INT(___VECTORLENGTH(m)) != 15) return 0;
 ___SCMOBJ extension=blc_ref(m,14);
 if (!___VECTORP(extension) || ___INT(___VECTORLENGTH(extension)) < 5
     || !___EQP(blc_ref(extension,0),___FIX(1))
     || !___EQP(blc_ref(extension,1),___FIX(1))) return 0;
 blc_set(extension,1,___FIX(2));
 return 1;
}
#define BLC_SKIP_NOACTOR_TICK(m) blc_skip_noactor_tick(m)
#define BLC_UNIT(m) blc_ref(m,0)
#define BLC_FRAME(m) blc_ref(m,2)
#define BLC_REG(m,r) blc_ref(BLC_FRAME(m),r)
#define BLC_CONST(m,k) blc_ref(blc_ref(BLC_UNIT(m),1),k)
#define BLC_PUT(m,r,v) blc_set(BLC_FRAME(m),r,v)
/* A C step has no callback/allocation/safepoint. Keep its unboxed PC local;
 * synchronize exactly once at EVERY step exit, before Scheme sees the machine.
 * ___WORD preserves the full fixnum even on an invalid/default diagnostic PC.
 */
#define BLC_PC(m,p) do { blc_pc=(p); } while(0)
#define BLC_YIELD(m,kind) do { blc_set(m,1,___FIX(blc_pc)); return (kind); } while(0)
#define BLC_TRUTHY(m,v) (!___FALSEP(v) && !___EQP(v,BLC_CONST(m,0)))
#define BLC_ACTION(m,a,d,n,p,t) do { blc_set(m,4,a); blc_set(m,5,___FIX(d)); \
 blc_set(m,6,___FIX(n)); blc_set(m,7,p); blc_set(m,8,(t)?___TRU:___FAL); } while(0)
/* Optional, non-raising NONTAIL raw BIFs. No allocation or callback. The
 * service procedure must be the exact frozen raw entry, not merely its name.
 * Extension fields0/1 belong to the shared version/tick protocol. */
#define BLC_PURE_BIF_V1 1
static int blc_try_pure_bif(___SCMOBJ m, int service, int id, int argc,
                          ___SCMOBJ a, ___SCMOBJ b, ___SCMOBJ *result) {
 ___SCMOBJ ___temp, e, originals, unit, services, value;
 ___WORD mask, seen, bit;
 if (___INT(___VECTORLENGTH(m)) != 15 || id<0 || id>3
     || argc != (id<2 ? 1 : 2)) return 0;
 e=blc_ref(m,14);
 if (!___VECTORP(e) || ___INT(___VECTORLENGTH(e))<5
     || !___EQP(blc_ref(e,0),___FIX(1))
     || !___FIXNUMP(blc_ref(e,2)) || !___FIXNUMP(blc_ref(e,4))) return 0;
 mask=___INT(blc_ref(e,2)); seen=___INT(blc_ref(e,4));
 if (mask<=0 || seen<0 || (seen & ~((___WORD)23))) return 0;
 originals=blc_ref(e,3); unit=blc_ref(m,0);
 if (!___VECTORP(originals) || ___INT(___VECTORLENGTH(originals))!=4
     || !___VECTORP(unit) || ___INT(___VECTORLENGTH(unit))!=5
     || !___EQP(blc_ref(unit,0),blc_ref(unit,4))) return 0;
 services=blc_ref(unit,2);
 if (!___VECTORP(services) || service<0 || service>=___INT(___VECTORLENGTH(services))
     || !___EQP(blc_ref(services,service),blc_ref(originals,id))) return 0;
 switch (id) {
  case 0:
   if (!(mask&1)) return 0;
   value=(___PAIRP(a)||___NULLP(a)) ? ___TRU : ___FAL; bit=1; break;
  case 1:
   /* Other exact/inexact numeric representations retain the original leaf. */
   if (!(mask&2) || !___FIXNUMP(a)) return 0;
   value=___TRU; bit=2; break;
  case 2:
   if (___EQP(a,b) && (mask&4)) value=___TRU;
   else if (___FIXNUMP(a) && ___FIXNUMP(b) && (mask&8)) value=___FAL;
   else return 0;
   bit=4; break;
  case 3:
   if (___EQP(a,b) && (mask&16)) value=___TRU;
   else if (___FIXNUMP(a) && ___FIXNUMP(b) && (mask&32)) value=___FAL;
   else return 0;
   bit=16; break;
  default: return 0;
 }
 *result=value;
 blc_set(e,4,___FIX(seen|bit));
 return 1;
}
#endif
