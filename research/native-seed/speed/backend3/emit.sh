#!/usr/bin/env bash
# both emissions in sequence (one work run slot)
set -uo pipefail
WT=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed/.claude/worktrees/r3-backend
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed
NS=$WT/research/native-seed; B3=$NS/speed/backend3
P=$MAIN/research/native-seed/out/speed-closure-2/partition.json
L=$MAIN/research/native-seed/out/round2-build/leaves.json
$B3/bl-src.sh $B3/out/old-src $WT run research/native-seed/speed/backend3/emit-rt.bl -- $P $L $B3/out/rt-orig.bl $B3/out/rt-base.scm
echo BASE_EXIT $?
$B3/bl-src.sh $NS/src $WT run research/native-seed/speed/backend3/emit-rt.bl -- $P $L priv/boot/rt.bl $B3/out/rt-new.scm $B3/out/rt-orig.bl $B3/out/rt-n1.scm
echo NEW_EXIT $?
