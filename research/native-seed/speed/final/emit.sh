#!/usr/bin/env bash
# Emit the 18-namespace native compiler on BEAM through bounded build-next windows.
set -uo pipefail
cd "$(dirname "$0")/../../../.."
seed=research/native-seed
out=$seed/out/speed-build
for i in $(seq 1 40); do
  line=$($seed/run run $seed/src/native/chunks.bl -- build-next \
    $seed/out/speed-closure/partition.json $out/host.scm $out $out/leaves.json 2>&1 | tee -a $out/emit.log | grep -E 'NATIVE_BUILD_(COMPLETE|YIELD)|Error' | tail -1)
  echo "window $i: $line"
  case "$line" in
    *NATIVE_BUILD_COMPLETE*) exit 0 ;;
    *NATIVE_BUILD_YIELD*) ;;
    *) echo "emission failed; see $out/emit.log"; exit 1 ;;
  esac
done
exit 1
