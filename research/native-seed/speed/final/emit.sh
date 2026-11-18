#!/usr/bin/env bash
# Emit the native compiler closure on BEAM through bounded build-next windows.
# Usage: emit.sh [CLOSURE_DIR] [BUILD_DIR]   (relative to research/native-seed)
set -euo pipefail
cd "$(dirname "$0")/../../../.."
seed=research/native-seed
closure=$seed/${1:-out/speed-closure}
out=$seed/${2:-out/speed-build}
for i in $(seq 1 60); do
  if ! line=$("$seed/run" run "$seed/src/native/chunks.bl" -- build-next \
    "$closure/partition.json" "$out/host.scm" "$out" "$out/leaves.json" 2>&1 |
    tee -a "$out/emit.log" | awk '/NATIVE_BUILD_(COMPLETE|YIELD)|Error|error/ {line = $0} END {print line}'); then
    echo "emission command failed in window $i; see $out/emit.log" >&2
    exit 1
  fi
  echo "window $i: $line"
  case "$line" in
    *NATIVE_BUILD_COMPLETE*) exit 0 ;;
    *NATIVE_BUILD_YIELD*) ;;
    *) echo "emission failed; see $out/emit.log"; exit 1 ;;
  esac
done
exit 1
