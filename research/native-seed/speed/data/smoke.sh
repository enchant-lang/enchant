#!/usr/bin/env bash
# Load the host sources + this workstream's host files + smoke.scm in gsi.
#   work run --memory 1G --timeout 900 -- bash research/native-seed/speed/data/smoke.sh
set -eu
ns="$(cd "$(dirname "$0")/../.." && pwd)"
out="$ns/speed/data/out"
mkdir -p "$out"
cd "$ns"
cat host.scm host/host-values.scm host/host-leaves.scm host/host-lazy.scm host/host-extra.scm \
    host/host-compiler.scm host/host-match.scm host/host-kernel.scm \
    host/native-gb-trees.scm host/native-data-bifs.scm speed/data/smoke.scm > "$out/smoke-run.scm"
timeout -s KILL 120 "$(jq -r .gambit toolchain-pin.json)/bin/gsi" "$out/smoke-run.scm"
