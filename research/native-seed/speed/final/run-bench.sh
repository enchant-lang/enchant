#!/usr/bin/env bash
# Run the prepared warm-core benchmark: native, then BEAM, one after the other,
# then compare. Usage: run-bench.sh BENCH_DIR (prepared by prepare.py).
set -euo pipefail
dir=$(realpath "$1")
argv() { python3 -c "import json,sys; print('\0'.join(json.load(open(sys.argv[1]))[sys.argv[2]]['argv']), end='')" "$dir/preparation.json" "$1"; }
mapfile -d '' native < <(argv native)
mapfile -d '' beam < <(argv beam)
timeout 600 "${native[@]}" > "$dir/native.log" 2>&1
timeout 600 "${beam[@]}" > "$dir/beam.log" 2>&1
python3 "$(dirname "$0")/../../benchmark/compare-benchmark.py" "$dir"
