#!/usr/bin/env bash
# cycle.sh MODE [EXTRA_NIX_ARGS] [STAGE.scm]: translate a stage, build it on the Build host, print rustc's cost.
# The built binary's path is written to $RS_WORK/bin-MODE.
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
T="${RS_WORK:?set RS_WORK to a scratch directory}"
mode="${1:-debug}"; extra="${2:-}"
stage="${3:-$here/../native-seed/out/cutover-core-build-v3/stage2.scm}"
B="$T/build"
rm -rf "$B/gen"; mkdir -p "$B/gen"
python3 -I "$here/translate.py" "$stage" "$B/gen" | head -1
cp "$here/rt.rs" "$here/main.rs" "$B/"
cd "$here"
nix build --impure -L --no-link --print-out-paths --expr "import ./measure.nix { src = $B; mode = \"$mode\"; $extra }" > "$T/$mode.log" 2>&1
P="$(tail -1 "$T/$mode.log")"
if [ -x "$P/bin/stage" ]; then
  tail -1 "$P/timing.txt"; echo "$P/bin/stage" > "$T/bin-$mode"
else
  grep -E "error" -A12 "$T/$mode.log" | sed 's/^rust-substrate-stage-[a-z]*> //' | head -60 | cut -c1-300
fi
