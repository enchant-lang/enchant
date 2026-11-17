#!/usr/bin/env bash
# FRAMES batch (one work run): old/new emission of the frames corpus, the
# rt/reader units with the new emitter, then the gsi programs and comparison.
set -uo pipefail
cd /home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed/.claude/worktrees/r3-frames
W=research/native-seed
R=$W/out/run-src.sh
if [ "${EMIT:-1}" = 1 ]; then
 $R $W/out/before-src -p $W/speed run $W/speed/frames/check.bl -- $W/out/frames-check old 2>&1 | tail -5
 $R $W/src -p $W/speed run $W/speed/frames/check.bl -- $W/out/frames-check new 2>&1 | tail -5
fi
if [ "${UNITS:-0}" = 1 ]; then
 $R $W/out/before-src run $W/speed/frames/emit-units.bl -- $W/out/frames-closure/partition.json $W/out/frames-closure/round2-leaves.json $W/out/frames-before rt,reader,reader-node 2>&1 | tail -5
 $R $W/src run $W/speed/frames/emit-units.bl -- $W/out/frames-closure/partition.json $W/out/frames-closure/round2-leaves.json $W/out/frames-after rt,reader,reader-node 2>&1 | tail -5
fi
python3 $W/speed/frames/run.py $W/out/frames-check
echo "FRAMES_JOB_EXIT $?"
