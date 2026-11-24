#!/usr/bin/env bash
# Card N0: the native front end against the BEAM's, per unit, same SDK, same units.
#
#   work run --memory 4G --timeout 2400 -- bash research/native-seed/front-end/n0/run.sh OUT setup
#   work run --memory 4G --timeout 2400 -- bash research/native-seed/front-end/n0/run.sh OUT native TAG
#   work run --memory 4G --timeout 2400 -- bash research/native-seed/front-end/n0/run.sh OUT beam TAG
#
# setup   derive chez-main with the N2b host edits (OUT/img), the BEAM's
#         custody and constructor kernel for the current SDK (OUT/out), the
#         front end as image units (n0/compose.py -> OUT/root), and a
#         candidate image that compiles them in (OUT/cand/image).
# native  the corpus on the candidate image: OUT/native-TAG.txt; the first
#         native run also makes the generated-module MD5 round trip
#         (front-end/generated-md5.bl, then a second native pass).
# beam    the same units on the BEAM in one fresh VM of the SDK's own bl:
#         OUT/beam-TAG.txt.
#         Repeat runs (TAG other than 1) write to OUT/out-TAG, so one can
#         run beside a BEAM run that reads run 1's unit files.
# Then: summarize.py OUT SDK NATIVE-TAGS BEAM-TAGS (n0/summarize.py).
# NF_ONLY="ns ..." limits a run to those units (a smoke check); N0_WARM and
# N0_REPS pick the warm-compile units and repeats.
set -u
WT=$(cd "$(dirname "$0")/../../../.." && pwd)
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
OUT=$1; STEP=$2; TAG=${3:-1}
WARM=${N0_WARM:-"reload.preinit-counter credential.pending diagnostics.otp bl.realm auth.audit"}
REPS=${N0_REPS:-5}
export BL_SDK_REUSE_CURRENT=1 QUALIFY_ROOT=$WT
# Every step after setup uses the SDK setup recorded (custody and kernel are
# that SDK's): the BEAM step runs that SDK's own bl, so main's current SDK
# may move on between steps.
SDK=$(readlink -f $MAIN/.bl/sdks/current-sdk)
[ "$STEP" != setup ] && SDK=$(cat $OUT/sdk)
PRIV=$SDK/image/priv
export BL_UNIT_STORE=$SDK/unit-store
FE=$WT/research/native-seed/front-end
mkdir -p $OUT
cd $WT
T() { local s=$(date +%s%N); "$@"; local rc=$?; echo "[$(( ($(date +%s%N) - s) / 1000000 )) ms, exit $rc]"; return $rc; }
B() { timeout 2400 $MAIN/bin/bl run "$@"; }
echo "sdk $SDK step $STEP tag $TAG $(uptime)"
case $STEP in
setup)
  echo $SDK > $OUT/sdk
  [ -d $OUT/img ] || T B research/native-seed/chez/qualify.bl -- derive --image $MAIN/research/native-seed/out/chez-main --out $OUT/img --base f4e4cec5c 2>&1 | tail -2
  echo "== custody"; T B $FE/custody.bl -- $OUT/out 2>&1 | tail -2
  echo "== kernel"; [ -f $OUT/out/kernel.etf ] || T timeout 1200 $MAIN/bin/bl --cold run $FE/kernel.bl -- $OUT/out/kernel.etf 2>&1 | tail -2
  echo "== compose"; T python3 -I $FE/n0/compose.py $PRIV $FE $OUT/root
  echo "== candidate"
  [ -d $OUT/cand ] || (T B research/native-seed/chez/qualify.bl -- candidate --image $OUT/img --out $OUT/cand \
      --source-root $OUT/root --additions $OUT/root/n0/additions.edn --codegen 2>&1 | tail -25)
  ;;
native)
  IMG=$OUT/cand/image
  # Repeat runs write their own unit files (OUT/out-TAG, same custody and
  # kernel, no generated MD5s, as run 1's first pass), so a BEAM run reading
  # run 1's files can go at the same time.
  D=$OUT/out
  if [ "$TAG" != 1 ] && [ "$TAG" != smoke ]; then
    D=$OUT/out-$TAG; mkdir -p $D
    ln -sf $OUT/out/custody.etf $D/custody.etf; ln -sf $OUT/out/kernel.etf $D/kernel.etf
    for n in $(ls $OUT/out/u); do mkdir -p $D/u/$n; done
  fi
  only=""; [ -n "${NF_ONLY:-}" ] && only="[$(for n in $NF_ONLY; do printf '"%s" ' $n; done)]"
  [ -z "$only" ] && only=nil
  warm="[$(for n in $WARM; do printf '"%s" ' $n; done)]"
  printf '(println "NF-STAGE-LOADED")\n(host.aot/nf-run %s %s %s %s %s)\n' "\"$D/custody.etf\"" "\"$D\"" "$only" "$warm" "$REPS" > $OUT/jobs-$TAG.bl
  echo "== native $TAG"
  T B research/native-seed/chez/qualify.bl -- eval --image $IMG --file $OUT/jobs-$TAG.bl > $OUT/native-$TAG.txt 2>&1
  echo "ok $(grep -c '^UNIT ok' $OUT/native-$TAG.txt) fail $(grep -c '^UNIT fail' $OUT/native-$TAG.txt)"
  grep -E '^(N0-|UNITS-DONE|WARM)' $OUT/native-$TAG.txt | head -40
  grep '^UNIT fail' $OUT/native-$TAG.txt | cut -c1-300 | head -8
  grep -v '^UNIT\|^WARM' $OUT/native-$TAG.txt | tail -c 2000
  if [ "$D" = $OUT/out ] && [ ! -f $OUT/out/generated-md5.etf ] && [ "$only" = nil ]; then
    echo "== generated-module round trip"
    T B $FE/generated-md5.bl -- $OUT/out 2>&1 | tail -2
    n2="[$(while read n; do printf '"%s" ' $n; done < $OUT/out/generated-units.txt)]"
    printf '(host.aot/nf-run %s %s %s [] 0)\n' "\"$OUT/out/custody.etf\"" "\"$OUT/out\"" "$n2" > $OUT/jobs-pass2.bl
    T B research/native-seed/chez/qualify.bl -- eval --image $IMG --file $OUT/jobs-pass2.bl > $OUT/native-pass2.txt 2>&1
    echo "pass 2: ok $(grep -c '^UNIT ok' $OUT/native-pass2.txt) fail $(grep -c '^UNIT fail' $OUT/native-pass2.txt)"
    grep -E '^(N0-|UNITS-DONE)' $OUT/native-pass2.txt
  fi
  ;;
beam)
  echo "== beam $TAG"
  T timeout 2400 $SDK/bin/bl --cold run $FE/n0/beam.bl -- $OUT/out $REPS $WARM > $OUT/beam-$TAG.txt 2>&1
  echo "ok $(grep -c '^BEAM ok' $OUT/beam-$TAG.txt) fail $(grep -c '^BEAM fail' $OUT/beam-$TAG.txt) same_desc $(grep -c 'same_desc true' $OUT/beam-$TAG.txt) same_core $(grep -c 'same_core true' $OUT/beam-$TAG.txt)"
  grep -E '^(BEAM-DONE|WARM|EVAL)' $OUT/beam-$TAG.txt | head -60
  grep '^BEAM fail' $OUT/beam-$TAG.txt | cut -c1-300 | head -8
  grep -v '^BEAM \|^WARM\|^EVAL' $OUT/beam-$TAG.txt | tail -c 2000
  ;;
esac
echo "done $(uptime)"
