#!/usr/bin/env bash
# Rebuild the one-body edit in a private overlay, then check selective relinking.
# --capture-local captures the qualified donor in the same overlay before
# making the edit. This keeps configured absolute loader roots exact.
# NATIVE_BOUND_REPLAY_EXPORT saves the checked closure ETF after bound replay.
# NATIVE_RELINK_COMPARE=1 runs the updater's checked candidate before the
# ordinary updater and compares both finished artifacts in the same overlay.
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
if [[ "${NATIVE_RELINK_COMPARE:-}" == 1 ]]; then
  [[ "$capture_local" == true && -z "${NATIVE_BOUND_REPLAY_EXPORT:-}" ]] || usage
fi
baseline=$(realpath "$1")
report=$(realpath -m "$2")
export_path=
if [[ -n "${NATIVE_BOUND_REPLAY_EXPORT:-}" ]]; then
  [[ "$capture_local" == true || -n "${receipt:-}" ]] || usage
  export_path=$(realpath -m "$NATIVE_BOUND_REPLAY_EXPORT")
fi
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
run_update() {
  local directory=$1
  shift
  systemd-run --user --quiet --collect --wait --pipe --working-directory="$overlay" \
    --property=MemoryMax=3G --property=MemorySwapMax=0 --property=RuntimeMaxSec=420 \
    --property=KillMode=control-group --setenv=XDG_RUNTIME_DIR="$overlay/runtime" \
    "$@" "$seed/speed/final/closure-r3.sh" "$directory"
}
if [[ "${NATIVE_RELINK_COMPARE:-}" == 1 ]]; then
  candidate=$seed/out/checked
  cp -a "$edited" "$candidate"
  request="$overlay/relink.json"
  python3 - "$request" "$receipt" "$samples" "$baseline/partition.json" "$qualification" "$receipt_sha" <<'PY'
import json
import sys
from pathlib import Path

request = dict(zip(("receipt", "samples", "donor", "qualification", "sha256"), sys.argv[2:], strict=True))
Path(sys.argv[1]).write_text(json.dumps(request))
PY
  run_update "$candidate" --setenv=NATIVE_RELINK_TIMINGS=1 --setenv=NATIVE_CHECKED_RELINK_REQUEST="$request"
  run_update "$edited" --setenv=NATIVE_RELINK_TIMINGS=1
  cmp "$candidate/closure.etf" "$edited/closure.etf"
  cmp "$candidate/link-rows.etf" "$edited/link-rows.etf"
  python3 - "$candidate" "$edited" "$report" <<'PY'
import json
import sys
from pathlib import Path

candidate_dir, clean_dir = map(Path, sys.argv[1:3])
candidate, clean = (json.loads((directory / "update.json").read_text())
                    for directory in (candidate_dir, clean_dir))
members = candidate["checked-relink"]["members"]
assert len(members) == len(clean["units"])
assert any(member["reused"] for member in members)
assert any(not member["reused"] for member in members)
assert candidate["artifact-sha256"] == clean["artifact-sha256"]

def timings(directory):
    return {
        phase: dict(zip(("wall", "user", "system"),
                        map(float, (directory / f"{phase}.seconds").read_text().split()),
                        strict=True))
        for phase in ("source-pass", "member-rows", "first-partition", "linked-pass", "final-partition")
    }

report = {"schema": "bl.native.checked-relink-comparison", "version": 2,
          "exact-closure": True, "exact-link-rows": True, "candidate": candidate, "clean": clean,
          "phase-seconds": {"candidate": timings(candidate_dir), "clean": timings(clean_dir)}}
Path(sys.argv[3]).write_text(json.dumps(report, indent=2) + "\n")
PY
  exit 0
fi
run_update "$edited"
if [[ -n "${receipt:-}" ]]; then
  mode=--bound-registry
  extra=()
  if [[ -n "$export_path" ]]; then
    mode=--bound-export
    extra+=("$export_path")
  fi
  "$seed/run" run "$seed/speed/front/observe-links.bl" -- "$edited/partition.json" \
    "$edited/link-rows.etf" "$mode" "$report" "$receipt" "$samples" \
    "$baseline/partition.json" "$qualification" "$receipt_sha" "${extra[@]}"
  if [[ -n "$export_path" ]]; then
    cmp "$export_path" "$edited/closure.etf"
  fi
else
  "$seed/run" run "$seed/speed/front/observe-links.bl" -- "$edited/partition.json" \
    "$edited/link-rows.etf" --source-shadow "$report" "$baseline/partition.json" "$overlay/baseline.etf"
fi
