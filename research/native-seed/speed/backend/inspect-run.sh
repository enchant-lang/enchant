#!/usr/bin/env bash
# AOT link-emission inspection with a chosen emitter source tree.
# cwd = the main checkout (its closure sources match the partition's pinned
# SHAs, read-only); BL code comes from SRC (new or previous scheme.bl).
# usage: inspect-run.sh SRC OUT SLOTS_FILE
set -euo pipefail
here=$(CDPATH='' cd "$(dirname "$0")/../.." && pwd -P)
src=$1 out=$2 slots=$3
main=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed
closure=$main/research/native-seed/out/speed-closure
sdk=$(jq -r .sdk "$here/sdk-pin.json")
source=$(jq -r .source "$here/sdk-pin.json")
runtime=$(mktemp -d /tmp/bl-backend-inspect-XXXXXXXX)
mkdir -p "$out"
systemd-run --user --quiet --collect --wait --pipe \
  --working-directory="$main" --property=MemoryMax=3G --property=MemorySwapMax=0 \
  --property=RuntimeMaxSec=600 --property=KillMode=control-group \
  --setenv=XDG_RUNTIME_DIR="$runtime" \
  "$sdk/bin/bl" --cold -p "$src" -p "$source/priv/build" \
  run "$src/native/chunks.bl" -- inspect "$closure/partition.json" "$closure/host.scm" "$out" \
  "$closure/leaves.json" "$(paste -sd, "$slots")"
rm -rf -- "$runtime"
