#!/usr/bin/env bash
# Round-3 final: chain (closure, image, self-emission compare), the source
# fixpoint and prepared evaluation bundle, then the BEAM vs native benchmark.
# Usage (repository root as cwd, under work run): final-r3.sh
set -euo pipefail
f=research/native-seed/speed/final
b=research/native-seed/out/round3-build
$f/chain-r3.sh || exit 1
python3 research/native-seed/fixpoint-full.py --root "$PWD" --out $b \
  --corpus research/native-seed/fixtures/compiler-source.bl --standard-bindings \
  --no-actors --prepare-eval-bundle > "$b/fixpoint.log" 2>&1
grep 'NATIVE_SOURCE_BOOTSTRAP_FIXPOINT' $b/fixpoint.log | tail -1
rm -rf research/native-seed/out/round3-bench
python3 $f/prepare.py --build $b --out research/native-seed/out/round3-bench > /dev/null
bash $f/run-bench.sh research/native-seed/out/round3-bench
