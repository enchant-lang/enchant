#!/usr/bin/env bash
# Rebuild the one-body edit in a private overlay, then check selective relinking.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo "usage: $0 QUALIFIED_CLOSURE_DIR REPORT.json" >&2
  exit 2
fi
baseline=$(realpath "$1")
report=$(realpath -m "$2")
root=$(cd "$(dirname "$0")/../../../.." && pwd -P)
cd "$root"
seed=research/native-seed
mkdir -p .local
overlay=$(mktemp -d "$root/.local/native-source-edit-XXXXXXXX")
trap 'rm -rf -- "$overlay"' EXIT
edited=$seed/out/edited
mkdir -p "$overlay/$edited" "$overlay/runtime" "$overlay/$seed/.runtime"
chmod 700 "$overlay/runtime"
printf '%s\n' "$overlay/runtime" > "$overlay/$seed/.runtime/path"
ln -s "$root/priv" "$overlay/priv"
for item in run sdk-pin.json partition-closure.py speed; do
  ln -s "$root/$seed/$item" "$overlay/$seed/$item"
done
cp -a --reflink=auto "$seed/src" "$overlay/$seed/src"
cp --reflink=auto "$baseline/partition.json" "$baseline/link-rows.etf" "$overlay/$edited/"
python3 - "$overlay/$seed/src/native/scheme.bl" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_bytes()
before = b'(Enum/join (cons "v" (Enum/map (unicode/characters_to_list s)'
after = b'(Enum/join (cons "w" (Enum/map (unicode/characters_to_list s)'
assert source.count(before) == 1, "the retained emitter body does not match the edit fixture"
path.write_bytes(source.replace(before, after, 1))
PY
"$seed/run" run "$seed/speed/front/observe-links.bl" -- "$baseline/partition.json" \
  "$baseline/link-rows.etf" --capture-source "$overlay/baseline.etf"
cd "$overlay"
systemd-run --user --quiet --collect --wait --pipe --working-directory="$overlay" \
  --property=MemoryMax=3G --property=MemorySwapMax=0 --property=RuntimeMaxSec=420 \
  --property=KillMode=control-group --setenv=XDG_RUNTIME_DIR="$overlay/runtime" \
  "$seed/speed/final/closure-r3.sh" "$edited"
"$seed/run" run "$seed/speed/front/observe-links.bl" -- "$edited/partition.json" \
  "$edited/link-rows.etf" --source-shadow "$report" "$baseline/partition.json" "$overlay/baseline.etf"
