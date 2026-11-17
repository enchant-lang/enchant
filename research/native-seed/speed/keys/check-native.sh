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
# The values differential compares round-2 raw map storage with today's. Q3
# changes exactly the non-canonical numeric keys, so print every failure and
# tally them by operation and key kind (see RESULT.md).
sed 's/(if (< diff-failures 20)/(if #t/' speed/values/values-diff-check.scm > "$out/values-diff-all.scm"
cat $common "$out/values-diff-all.scm" > "$out/values-diff.scm"
timeout -s KILL 300 "$gsi" "$out/values-diff.scm" > "$out/values-diff.log" 2>&1 || true
# Only map storage/lookup may differ: the random maps mix -0.0, 1.0 and
# decimals with integers, which Q3 now merges, and a `bl-map literal` row
# looks a float/decimal key up through the canonical `bl-get` in a map built
# raw. Every other comparison (key order, keywords, strings, struct fields,
# equality) must stay identical to the round-2 host.
other=$(grep "^DIFF FAIL" "$out/values-diff.log" | grep -v "^DIFF FAIL random map" \
        | grep -v "^DIFF FAIL bl-map literal.*\(float\|Decimal\)" | wc -l)
echo "values-diff: $(tail -1 "$out/values-diff.log"); failures outside numeric-key map storage: $other"
[ "$other" = 0 ] || { grep "^DIFF FAIL" "$out/values-diff.log" | grep -v "^DIFF FAIL random map" | head -5; exit 1; }
grep -o "DIFF FAIL [a-z /?!-]*:" "$out/values-diff.log" | sort | uniq -c || true
grep -h "checks\|PASS\|passed" "$out"/values.log "$out"/memo.log "$out"/extra.log "$out"/values-diff.log
