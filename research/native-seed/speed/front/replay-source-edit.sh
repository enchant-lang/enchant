#!/usr/bin/env bash
# Rebuild the one-body edit in a private overlay, then check selective relinking.
# --capture-local captures the qualified donor in the same overlay before
# making the edit. This keeps configured absolute loader roots exact.
set -euo pipefail
usage() {
  echo "usage: $0 QUALIFIED_CLOSURE_DIR REPORT.json [RECEIPT RECEIPT_SHA QUALIFICATION PHASE_MACRO_SAMPLES [--arity]]" >&2
  echo "       $0 QUALIFIED_CLOSURE_DIR REPORT.json --capture-local QUALIFICATION PHASE_MACRO_SAMPLES [--arity]" >&2
  exit 2
}
capture_local=false
edit=
if [[ "${3:-}" == --capture-local ]]; then
  [[ $# == 5 || $# == 6 ]] || usage
  capture_local=true
  qualification=$(realpath "$4")
  samples=$(realpath "$5")
  edit=${6:-}
elif [[ $# == 6 || $# == 7 ]]; then
  receipt=$(realpath "$3")
  receipt_sha=$4
  qualification=$(realpath "$5")
  samples=$(realpath "$6")
  edit=${7:-}
else
  [[ $# == 2 ]] || usage
fi
[[ -z "$edit" || "$edit" == --arity ]] || usage
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
if "$capture_local"; then
  receipt="$overlay/bound-donor.etf"
  (
    cd "$overlay"
    "$seed/run" run "$seed/speed/front/observe-links.bl" -- "$baseline/partition.json" \
      "$baseline/link-rows.etf" --capture-bound-registry "$receipt" "$samples" "$qualification"
  )
  receipt_sha=$(sha256sum "$receipt")
  receipt_sha=${receipt_sha%% *}
fi
python3 - "$overlay/$seed/src/native/scheme.bl" "$edit" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_bytes()
if sys.argv[2] == "--arity":
    body = b'(Enum/join (cons "v" (Enum/map (unicode/characters_to_list s) (fn [c] (code-text c)))) "")'
    before = b'(defn ident [s]\n ' + body + b')'
    after = b'(defn ident\n ([s] ' + body + b')\n ([s prefix] (str prefix (ident s))))'
else:
    before = b'(Enum/join (cons "v" (Enum/map (unicode/characters_to_list s)'
    after = b'(Enum/join (cons "w" (Enum/map (unicode/characters_to_list s)'
assert source.count(before) == 1, "the retained emitter body does not match the edit fixture"
path.write_bytes(source.replace(before, after, 1))
PY
if [[ -z "${receipt:-}" ]]; then
  "$seed/run" run "$seed/speed/front/observe-links.bl" -- "$baseline/partition.json" \
    "$baseline/link-rows.etf" --capture-source "$overlay/baseline.etf"
fi
cd "$overlay"
systemd-run --user --quiet --collect --wait --pipe --working-directory="$overlay" \
  --property=MemoryMax=3G --property=MemorySwapMax=0 --property=RuntimeMaxSec=420 \
  --property=KillMode=control-group --setenv=XDG_RUNTIME_DIR="$overlay/runtime" \
  "$seed/speed/final/closure-r3.sh" "$edited"
if [[ -n "${receipt:-}" ]]; then
  "$seed/run" run "$seed/speed/front/observe-links.bl" -- "$edited/partition.json" \
    "$edited/link-rows.etf" --bound-registry "$report" "$receipt" "$samples" \
    "$baseline/partition.json" "$qualification" "$receipt_sha"
else
  "$seed/run" run "$seed/speed/front/observe-links.bl" -- "$edited/partition.json" \
    "$edited/link-rows.etf" --source-shadow "$report" "$baseline/partition.json" "$overlay/baseline.etf"
fi
