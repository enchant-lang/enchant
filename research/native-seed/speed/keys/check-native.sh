#!/usr/bin/env bash
# Native host checks for Q3 keys: the new key fixture plus the existing host
# value/raw-leaf fixtures that touch map keys, each in gsi under a 120 s cap.
#   work run --memory 1G --timeout 900 -- bash research/native-seed/speed/keys/check-native.sh
set -eu
ns="$(cd "$(dirname "$0")/../.." && pwd)"
out="$ns/speed/keys/out"
mkdir -p "$out"
cd "$ns"
gsi="$(jq -r .gambit toolchain-pin.json)/bin/gsi"
common="host.scm host/host-values.scm host/host-leaves.scm host/host-extra.scm host/native-memo.scm"
run() { # label, fixtures...
  label="$1"; shift
  cat $common "$@" > "$out/$label.scm"
  timeout -s KILL 120 "$gsi" "$out/$label.scm" > "$out/$label.log" 2>&1 || { echo "$label FAIL"; tail -20 "$out/$label.log"; exit 1; }
  echo "$label PASS: $(tail -1 "$out/$label.log")"
}
run keys speed/keys/native-keys-check.scm
run values fixtures/host-values-check.scm
run memo fixtures/native-memo-check.scm
run extra fixtures/host-extra-check.scm fixtures/host-symbol-name-check.scm fixtures/host-raw-map-get-check.scm \
    fixtures/host-array-check.scm fixtures/host-runtime-id-check.scm fixtures/host-input-wait-check.scm
grep -h "checks\|PASS\|passed" "$out"/values.log "$out"/memo.log "$out"/extra.log
