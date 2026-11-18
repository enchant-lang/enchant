#!/usr/bin/env bash
# Run one prepared native attribution (prepare.py) and keep its log.
# Usage (always under the account's batch cap):
#   work run --memory 4G --timeout 1800 -- speed/attrib/run-native.sh RUN_DIR
set -euo pipefail
dir=$(realpath "$1")
mapfile -d '' argv < <(python3 -c "import json,sys; print('\0'.join(json.load(open(sys.argv[1]))['argv']), end='')" "$dir/preparation.json")
status=0
timeout 1500 "${argv[@]}" > "$dir/native.log" 2>&1 || status=$?
printf 'exit %d\n' "$status" >> "$dir/native.log"
exit "$status"
