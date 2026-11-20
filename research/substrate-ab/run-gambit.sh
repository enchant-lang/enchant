#!/usr/bin/env bash
# Usage: run-gambit.sh IMAGE IN_DIR OUT_DIR REPS — times the reader job on a Gambit image.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); image=$1; in=$2; out=$3; reps=${4:-8}
mkdir -p "$out"
sed -e "s|@SOURCE@|$in/reader.bl|" -e "s|@BUNDLE@|$in/eval-prepared.scm|" -e "s|@OUT@|$out|" -e "s|@REPS@|$reps|" \
  "$here/gambit-shim.scm" > "$out/run.scm"
cat "$here/observer.scm" >> "$out/run.scm"
/usr/bin/env time -f "AB_PROCESS wall %e user %U sys %S maxrss_kb %M" "$image" --eval "$out/run.scm" "$in/eval-prepared.scm"
