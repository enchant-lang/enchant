#!/usr/bin/env bash
# Differential reader check, one pinned-SDK VM at a time (each call is capped
# at 3 GiB / 240 s by research/native-seed/run). `reader` is the pinned SDK's
# compiled reader (the pre-cutover source, byte-identical to priv/boot/reader.bl
# at the fan-out base); `reader2` is priv/boot/reader.bl of THIS checkout,
# loaded under a renamed namespace next to it. The small list and the error
# corpus go first; the full shards run only when that pass is clean.
set -uo pipefail
cd "$(dirname "$0")/../../../.."
out=${READER_DIFF_OUT:-/home/othman/.claude/jobs/bbc0cb7e/tmp/reader-diff}
list=${READER_DIFF_LIST:-/home/othman/.claude/jobs/bbc0cb7e/tmp/reader-files.txt}
shards=${READER_DIFF_SHARDS:-6}
mkdir -p "$out/src"
# Corpus: every .bl under priv/ and research/native-seed/src, and every fifth
# test/bl file; the small list carries the error corpus pass.
if [[ ! -f "$list" ]]; then
  { find priv research/native-seed/src -type f -name '*.bl' | sort
    find test/bl -type f -name '*.bl' | sort | awk 'NR%5==1'; } > "$list"
fi
small="$out/small.txt"
printf 'priv/boot/reader.bl\npriv/boot/diag.bl\n' > "$small"
sed 's/^(ns reader$/(ns reader2/' priv/boot/reader.bl > "$out/src/reader2.bl"
grep -q '^(ns reader2$' "$out/src/reader2.bl" || { echo "could not rename the reader namespace"; exit 1; }
run() { research/native-seed/run run -p "$out/src" research/native-seed/speed/reader/diff.bl -- "$@"; }
run "$small" 0 1 research/native-seed/speed/reader/errors.txt > "$out/corpus.txt" 2>&1
if ! grep -q "^DIFF .* mismatches 0$" "$out/corpus.txt"; then
  echo "corpus pass not clean; see $out/corpus.txt"; tail -40 "$out/corpus.txt"; exit 1
fi
grep "^DIFF" "$out/corpus.txt"
for ((i = 0; i < shards; i++)); do
  run "$list" "$i" "$shards" > "$out/shard-$i.txt" 2>&1
  grep "^DIFF" "$out/shard-$i.txt" || { echo "shard $i failed"; tail -20 "$out/shard-$i.txt"; }
done
! grep -h "^MISMATCH" "$out"/shard-*.txt | head -20
