#!/usr/bin/env bash
# Round-3 closure update: pass 1 refreshes changed sources, then pass 2
# compiles against the member link rows or reuses an exact linked generation.
# Usage: closure-r3.sh CLOSURE_DIR [--prepare|--link] (repository root as cwd)
set -euo pipefail
dir=$1
mode=${2:-}
[[ $# -le 2 && ( -z "$mode" || "$mode" == --prepare || "$mode" == --link ) ]] || exit 2
pin=research/native-seed/sdk-pin.json
sdk=$(python3 -c "import json;print(json.load(open('$pin'))['sdk'])")
src=$(python3 -c "import json;print(json.load(open('$pin'))['source'])")
bl() { "$sdk/bin/bl" --cold -p research/native-seed/src -p "$src/priv/build" "$@"; }
phase() {
  local label=$1
  shift
  if [[ -z "${NATIVE_RELINK_TIMINGS:-}" ]]; then
    "$@"
  else
    local TIMEFORMAT='%3R %3U %3S'
    { time "$@" 2>&3; } 3>&2 2>"$dir/$label.seconds"
  fi
}
if [[ "$mode" != --link ]]; then
NATIVE_PRIOR_LINK_ROWS="$dir/link-rows.etf" phase source-pass bl run research/native-seed/src/native/update-closure.bl -- "$dir/partition.json"
# The update read and checked every original partition. It can keep that exact
# generation when the current linked context and the serialized ETF still match.
if python3 - "$dir" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
update = json.loads((root / 'update.json').read_text())
partition = json.loads((root / 'partition.json').read_text())
if not update['linked-context-reused']:
    sys.exit(1)
actual = hashlib.sha256((root / 'closure.etf').read_bytes()).hexdigest()
sys.exit(0 if actual == update['artifact-sha256'] == partition['artifact_sha256'] else 1)
PY
then
  echo 'NATIVE_LINKED_CLOSURE_REUSED exact closure and partitions'
  exit 0
fi
phase member-rows bl run research/native-seed/src/native/member-rows.bl -- "$dir/closure.etf" "$dir/link-rows.etf"
phase first-partition python3 research/native-seed/partition-closure.py --out "$dir"
fi
if [[ "$mode" == --prepare ]]; then exit 0; fi
NATIVE_LINK_ROWS="$dir/link-rows.etf" phase linked-pass bl run research/native-seed/src/native/update-closure.bl -- "$dir/partition.json"
phase final-partition python3 research/native-seed/partition-closure.py --out "$dir"
