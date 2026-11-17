#!/usr/bin/env bash
# AOT link emission of the named definitions of the round-2 closure
# (MAIN/NS/out/speed-closure-2) with a chosen emitter source tree, through
# native.chunks inspect. cwd = the main checkout, read-only: its closure
# sources match the partition's pinned SHAs. Run it under `work run`.
# usage: inspect-run.sh SRC OUT SLOTS_FILE
set -euo pipefail
here=$(CDPATH='' cd "$(dirname "$0")" && pwd -P)
src=$(CDPATH='' cd "$1" && pwd -P) out=$2 slots=$3
main=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed
closure=$main/research/native-seed/out/speed-closure-2
mkdir -p "$out"
exec "$here/bl-src.sh" "$src" "$main" run "$src/native/chunks.bl" -- inspect "$closure/partition.json" \
  "$closure/host.scm" "$out" "$closure/leaves.json" "$(paste -sd, "$slots")"
