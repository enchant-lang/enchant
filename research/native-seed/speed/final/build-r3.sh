#!/usr/bin/env bash
# Round-3 native image: host checks, host, chunk emission, stage-1 ELF.
# Usage (repository root as cwd, under work run): build-r3.sh
set -euo pipefail
seed=research/native-seed
python3 $seed/check-host.py --out "$TMPDIR/host-r3"
python3 $seed/prepare-host.py --out $seed/out/round3-build | tail -1
bash $seed/speed/final/emit.sh out/speed-closure-3 out/round3-build
cp $seed/out/speed-closure-3/identity.json $seed/out/round3-build/
python3 $seed/fixpoint-full.py --root "$PWD" --out $seed/out/round3-build \
  --corpus $seed/fixtures/compiler-source.bl --compile-stage1-only --standard-bindings
