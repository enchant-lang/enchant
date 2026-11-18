#!/usr/bin/env bash
# Round-3 closure update: pass 1 refreshes changed sources, then pass 2
# compiles against the member link rows or reuses an exact linked generation.
# Usage: closure-r3.sh CLOSURE_DIR   (repository root as cwd; runs under work run)
set -euo pipefail
dir=$1
pin=research/native-seed/sdk-pin.json
sdk=$(python3 -c "import json;print(json.load(open('$pin'))['sdk'])")
src=$(python3 -c "import json;print(json.load(open('$pin'))['source'])")
bl() { "$sdk/bin/bl" --cold -p research/native-seed/src -p "$src/priv/build" "$@"; }
bl run research/native-seed/src/native/update-closure.bl -- "$dir/partition.json"
bl run research/native-seed/src/native/member-rows.bl -- "$dir/closure.etf" "$dir/link-rows.etf"
python3 research/native-seed/partition-closure.py --out "$dir"
NATIVE_LINK_ROWS="$dir/link-rows.etf" bl run research/native-seed/src/native/update-closure.bl -- "$dir/partition.json"
python3 research/native-seed/partition-closure.py --out "$dir"
