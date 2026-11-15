/* Fixed C action-boundary probe only. No BL/ANF decoder or execution policy. */
#include "native-direct.h"
#if BL_NATIVE_DIRECT_ABI != 2 || !defined(BLC_YIELD)
#error local_PC_probe_requires_current_ABI2_header
#endif

static void pc_probe_action_fields(___SCMOBJ m, int kind) {
 switch (kind) {
 case BLC_SERVICE:
  blc_set(m,11,BLC_CONST(m,5));
  BLC_ACTION(m,___FIX(2),4,89,BLC_CONST(m,3),0); break;
 case BLC_CALL:
  blc_set(m,11,BLC_CONST(m,5));
  BLC_ACTION(m,BLC_REG(m,3),4,89,BLC_CONST(m,3),1); break;
 case BLC_RETURN:
  blc_set(m,4,BLC_REG(m,3)); break;
 case BLC_CLOSURE:
  blc_set(m,11,BLC_CONST(m,0));
  BLC_ACTION(m,BLC_CONST(m,4),4,89,BLC_CONST(m,3),0); break;
 case BLC_TICK:
  blc_set(m,11,BLC_CONST(m,0));
  BLC_ACTION(m,___FIX(0),0,89,___NUL,0); break;
 case BLC_CALL_SLOTS:
  blc_set(m,11,BLC_CONST(m,5));
  BLC_ACTION(m,BLC_REG(m,3),4,89,BLC_CONST(m,3),1); break;
 }
}

/* The preceding emitter's exact PC discipline: store on every pure edge,
 * reload at the switch, and return without an additional PC store. */
#define PC_OLD_EDGE(m,p) blc_set(m,1,___FIX(p))
static int pc_probe_original(___SCMOBJ m, int kind) {
 for (;;) { switch ((int)___INT(blc_ref(m,1))) {
 case 0:
  BLC_PUT(m,1,BLC_CONST(m,1)); BLC_PUT(m,2,BLC_CONST(m,2));
  PC_OLD_EDGE(m,11); continue;
 case 11:
  BLC_PUT(m,3,BLC_REG(m,1));
  PC_OLD_EDGE(m,BLC_TRUTHY(m,BLC_REG(m,2))?47:53); continue;
 case 47: case 53:
  pc_probe_action_fields(m,kind); return kind;
 default: return -1;
 } }
}

static int pc_probe_local(___SCMOBJ m, int kind) {
 ___WORD blc_pc=___INT(blc_ref(m,1));
 for (;;) { switch ((int)blc_pc) {
 case 0:
  BLC_PUT(m,1,BLC_CONST(m,1)); BLC_PUT(m,2,BLC_CONST(m,2));
  BLC_PC(m,11); continue;
 case 11:
  BLC_PUT(m,3,BLC_REG(m,1));
  BLC_PC(m,BLC_TRUTHY(m,BLC_REG(m,2))?47:53); continue;
 case 47: case 53:
  pc_probe_action_fields(m,kind); BLC_YIELD(m,kind);
 default: BLC_YIELD(m,-1);
 } }
}
