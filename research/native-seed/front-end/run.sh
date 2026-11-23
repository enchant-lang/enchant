#!/usr/bin/env bash
# Card N2b: one native front-end run over the current SDK's units.
#
#   work run --memory 4G --timeout 2400 -- bash -lc \
#     'bash research/native-seed/front-end/run.sh TAG simple|all [derive]'
#
# 1. derive  the main native image plus this tree's host/*.scm edits (against
#            BASE, the commit chez-main was qualified at), only when asked or
#            when OUT/img does not exist yet;
# 2. custody the BEAM's per-unit custody facts (front-end/custody.bl);
# 3. native  lower-core.bl lower.bl hook.bl aot.bl(hooked) stage.bl jobs.bl,
#            evaluated by the native image, all taken from the SDK's own priv;
# 4. compare the BEAM's own preparation of each unit against the native
#            descriptors and Core (front-end/compare.bl).
# Everything lands under .qualify-out/nf-TAG (untracked).
set -u
WT=$(cd "$(dirname "$0")/../../.." && pwd)
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
BASE=${NF_BASE:-f4e4cec5c}
TAG=$1; MODE=$2; STEP=${3:-}
export BL_SDK_REUSE_CURRENT=1 QUALIFY_ROOT=$WT
SDK=$(readlink -f $MAIN/.bl/sdks/current-sdk)
PRIV=$SDK/image/priv
export BL_UNIT_STORE=$SDK/unit-store
Q=$WT/.qualify-out/nf-$TAG; FE=$WT/research/native-seed/front-end
IMG=${NF_IMAGE:-$Q/img}
mkdir -p $Q
cd $WT
exec > >(tee $Q/progress.log) 2>&1
T() { local s=$(date +%s%N); "$@"; local rc=$?; echo "[$(( ($(date +%s%N) - s) / 1000000 )) ms, exit $rc]"; return $rc; }
B() { timeout 2400 $MAIN/bin/bl run "$@"; }
echo "sdk $SDK image $IMG base $BASE"
if [ "$STEP" = derive ] || [ ! -d $IMG ]; then
  echo "== derive"
  T B research/native-seed/chez/qualify.bl -- derive --image $MAIN/research/native-seed/out/chez-main --out $IMG --base $BASE 2>&1 | tail -3
fi
if [ "${NF_QUALIFY:-}" = 1 ]; then
  echo "== qualify"
  T B research/native-seed/chez/qualify.bl -- qualify --image $IMG --work $Q/qualify 2>&1 | grep -E "GATE|STATUS|rror" | cut -c1-200
fi
echo "== custody"
T B $FE/custody.bl -- $Q/out $MODE 2>&1 | tail -3
# kernel.bl traces calls VM-wide, so it runs in a cold VM; NF_KERNEL reuses
# an earlier capture of the same SDK.
if [ -n "${NF_KERNEL:-}" ]; then cp $NF_KERNEL $Q/out/kernel.etf
elif [ ! -f $Q/out/kernel.etf ]; then T timeout 1200 $MAIN/bin/bl --cold run $FE/kernel.bl -- $Q/out/kernel.etf 2>&1 | tail -3; fi
sed 's#BeamLisp\.Emit/compile_descriptor#native-front.hook/compile-descriptor#g' $PRIV/host/aot.bl > $Q/aot-hooked.bl
echo "hooked sites $(grep -c 'native-front.hook/compile-descriptor' $Q/aot-hooked.bl)"
JOB=$(cat $Q/out/jobs.bl)
if [ -n "${NF_ONLY:-}" ]; then JOB="${JOB%)} [$(for n in $NF_ONLY; do printf '"%s" ' $n; done)])"; fi
{ echo '(println "NF-STAGE-LOADED")'
  [ -f "${NF_EXTRA:-}" ] && cat $NF_EXTRA
  echo "(try $JOB (catch e (println (str \"NF-TOP \" (pr-str e)))))"; } > $Q/jobs.bl
python3 $FE/loader-decls.py $PRIV/host/loader.bl $Q/loader-decls.bl
# host.record names itself with a fun literal; the native linker answers that
# for image modules only, so the evaluated copy is told its module.
printf '(ns host.record)\n(defn- self-mod [] :Elixir.BeamLisp.Record)\n' > $Q/record-self.bl
cat $PRIV/boot/lower-core.bl $PRIV/boot/lower.bl $FE/hook.bl $PRIV/host/record.bl $Q/record-self.bl $Q/aot-hooked.bl $Q/loader-decls.bl $FE/stage.bl $Q/jobs.bl > $Q/native.bl
echo "== native front"
T B research/native-seed/chez/qualify.bl -- eval --image $IMG --file $Q/native.bl > $Q/native.txt 2>&1
echo "ok $(grep -c '^UNIT ok' $Q/native.txt) fail $(grep -c '^UNIT fail' $Q/native.txt)"
grep "^UNIT fail" $Q/native.txt | sed -E 's/^UNIT fail [^ ]+ //' | cut -c1-240 | sort | uniq -c | sort -rn | head -30
grep "^UNIT-STACK" $Q/native.txt | sort -u -k3 | cut -c1-1500 | head -12
grep -v "^UNIT" $Q/native.txt | tail -c ${NF_TAIL:-3000}
[ "${NF_COMPARE:-1}" = 0 ] && exit 0
echo "== compare"
T B $FE/compare.bl -- $Q/out > $Q/compare.txt 2>&1
grep "^FRONT-DIFF" $Q/compare.txt | cut -c1-${NF_DIFF_WIDTH:-400}
grep -v "^FRONT-DIFF" $Q/compare.txt | tail -30
