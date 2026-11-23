#!/usr/bin/env bash
# Card N2b: native map iteration order against the BEAM's.
#
#   bash research/native-seed/front-end/hamt-check.sh IMAGE FILE.bl ...
#
# Each FILE builds maps and prints `M<id> <values in iteration order>`
# (front-end/hamt-keys.py writes such files). Runs each on the BEAM and on
# IMAGE (qualify.bl eval) and reports, per file, maps equal / differing.
set -u
WT=$(cd "$(dirname "$0")/../../.." && pwd)
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
export BL_SDK_REUSE_CURRENT=1 QUALIFY_ROOT=$WT
IMG=$1; shift
cd $WT
for f in "$@"; do
  $MAIN/bin/bl run $f > $f.beam 2>&1
  $MAIN/bin/bl run research/native-seed/chez/qualify.bl -- eval --image $IMG --file $f > $f.native 2>&1
  python3 -I - "$f" <<'PY'
import sys
f=sys.argv[1]
def rows(p): return {l.split(" ",1)[0]: l.rstrip("\n") for l in open(p) if l.startswith("M")}
b, n = rows(f+".beam"), rows(f+".native")
same = sum(1 for k in b if n.get(k) == b[k])
bad = sorted((k for k in b if n.get(k) != b[k]), key=lambda k: int(k[1:]) if k[1:].isdigit() else 0)
print("%s maps %d equal %d differ %d%s" % (f, len(b), same, len(bad), (" first " + " ".join(bad[:8])) if bad else ""))
PY
done
