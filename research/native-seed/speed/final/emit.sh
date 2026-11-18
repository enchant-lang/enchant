#!/usr/bin/env bash
# Emit the native compiler closure on BEAM through bounded build-next windows.
# Usage: emit.sh [CLOSURE_DIR] [BUILD_DIR]   (relative to research/native-seed)
set -euo pipefail
cd "$(dirname "$0")/../../../.."
seed=research/native-seed
closure=$seed/${1:-out/speed-closure}
out=$seed/${2:-out/speed-build}
resume=
for i in $(seq 1 60); do
  if ! line=$(NATIVE_CHUNK_PLAN_SHA=$resume "$seed/run" run "$seed/src/native/chunks.bl" -- build-next \
    "$closure/partition.json" "$out/host.scm" "$out" "$out/leaves.json" 2>&1 |
    tee -a "$out/emit.log" | awk '/NATIVE_BUILD_(COMPLETE|YIELD)|Error|error/ {line = $0} END {print line}'); then
    echo "emission command failed in window $i; see $out/emit.log" >&2
    exit 1
  fi
  echo "window $i: $line"
  case "$line" in
    *NATIVE_BUILD_COMPLETE*) exit 0 ;;
    *NATIVE_BUILD_YIELD*)
      resume=${line##* plan_sha=}
      [[ $resume =~ ^[a-f0-9]{64}$ ]] || { echo "invalid plan digest in window $i" >&2; exit 1; }
      ;;
    *) echo "emission failed; see $out/emit.log"; exit 1 ;;
  esac
done
exit 1
