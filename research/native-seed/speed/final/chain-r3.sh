#!/usr/bin/env bash
# Round-3 chain: closure update, image build, native self-emission, comparison.
# Usage (repository root as cwd, under work run): chain-r3.sh
set -uo pipefail
f=research/native-seed/speed/final
b=research/native-seed/out/round3-build
mkdir -p .local/round3
$f/closure-r3.sh research/native-seed/out/speed-closure-3 > .local/round3/update-closure.log 2>&1 || { echo CLOSURE_FAILED; exit 1; }
TMPDIR=${TMPDIR:-/tmp} $f/build-r3.sh > $b/build-r3.log 2>&1 || { echo BUILD_FAILED; exit 1; }
$f/self-emit-r3.sh > $b/self-emit.log 2>&1
python3 $f/compare-stages.py $b
