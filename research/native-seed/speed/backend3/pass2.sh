#!/usr/bin/env bash
# BACKEND round 3, second pass: every emission of the checks, in one work run.
# OLD = the integrated tip before this pass (out/r2/old-src, git archive of
# HEAD at 12241b695); NEW = this worktree's src. The pinned SDK predates
# Elixir.BeamLisp.Facts, so each run goes through facts-run.bl.
# usage: work run --memory 4G --timeout 10800 -- research/native-seed/speed/backend3/pass2.sh
set -uo pipefail
WT=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed/.claude/worktrees/r3-backend
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed
NS=$WT/research/native-seed; B3=$NS/speed/backend3; O=$B3/out/r2
FACTS=$WT/priv/host/facts.bl
P=$MAIN/research/native-seed/out/speed-closure-2/partition.json
L=$MAIN/research/native-seed/out/round2-build/leaves.json
C=$MAIN/research/native-seed/out/speed-closure-2
FR=$MAIN/.claude/worktrees/r3-frames/research/native-seed/out/frames-check
run() { src=$1 cwd=$2; shift 2; "$B3/bl-src.sh" "$src" "$cwd" "$@"; }
if [ "${RT:-1}" = 1 ]; then
 run $O/old-src $WT run $B3/facts-run.bl -- $FACTS $B3/emit-rt.bl $P $L $O/rt-head.bl $O/rt-base.scm; echo RT_OLD_EXIT $?
 run $NS/src $WT run $B3/facts-run.bl -- $FACTS $B3/emit-rt.bl $P $L $O/rt-head.bl $O/rt-new.scm; echo RT_NEW_EXIT $?
fi
if [ "${INSPECT:-1}" = 1 ]; then
 # every named definition of the closure, through bootstrap/emit-definition (emit-closure.bl)
 run $O/old-src $WT run $B3/facts-run.bl -- $FACTS $B3/emit-closure.bl $P $L $O/closure-old.scm; echo CLOSURE_OLD_EXIT $?
 run $NS/src $WT run $B3/facts-run.bl -- $FACTS $B3/emit-closure.bl $P $L $O/closure-new.scm; echo CLOSURE_NEW_EXIT $?
fi
if [ "${EQ:-1}" = 1 ]; then
 run $NS/src $NS -p $NS/speed run $B3/facts-run.bl -- $FACTS $B3/equality.bl $O/eq benchmark/compiler-values.bl \
  speed/control/corpus.bl src/native/scheme.bl src/native/eval.bl src/native/resolution.bl src/native/intrinsics.bl
 echo EQ_EXIT $?
fi
if [ "${FRAMES:-1}" = 1 ]; then
 # FRAMES harness: its pre-N4 reference (old-*.scm, old-host) is FRAMES's own; NEW is emitted here.
 mkdir -p $O/frames-check
 cp -r $FR/old-release.scm $FR/old-frames.scm $FR/old-host $O/frames-check/
 (cd $WT && "$B3/bl-src.sh" $NS/src $WT -p $NS/speed run $B3/facts-run.bl -- $FACTS $NS/speed/frames/check.bl $O/frames-check new) 2>&1 | tail -3
 echo FRAMES_EMIT_EXIT $?
 python3 $NS/speed/frames/run.py $O/frames-check; echo FRAMES_RUN_EXIT $?
fi
