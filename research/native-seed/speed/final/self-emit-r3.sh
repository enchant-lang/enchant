#!/usr/bin/env bash
# Native self-emission: stage1 compiles its own bundle (240 s deadline, as
# fixpoint-full.py), then stage2.scm is compared byte for byte with stage1.scm.
# Usage (repository root as cwd, under work run): self-emit-r3.sh
set -uo pipefail
b=research/native-seed/out/round3-build
rm -f $b/stage2.scm
start=$(date +%s.%N)
timeout 240 env BL_NATIVE_TRACE=0 $b/stage1 --compile $b/bundle.scm $b/host.scm $b/stage2.scm
status=$?
echo "SELF_EMIT exit=$status seconds=$(echo "$(date +%s.%N) - $start" | bc)"
[ $status -eq 0 ] || exit $status
sha256sum $b/stage1.scm $b/stage2.scm
if cmp -s $b/stage1.scm $b/stage2.scm; then echo STAGE1_EQUALS_STAGE2; else cmp $b/stage1.scm $b/stage2.scm | head -1; echo STAGE1_DIFFERS_STAGE2; fi
