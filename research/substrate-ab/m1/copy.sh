# M1: make a private copy of the Enchant checkout that runs on main's client and
# main's SDK without preparing anything.
#   usage: bash copy.sh MAIN COPY [REV]  (COPY must not exist; REV defaults to HEAD)
# It adds a detached `git worktree` of MAIN's HEAD at COPY, then links the
# copy's .bl state to the store paths MAIN already selected: the checkout
# platform (client), its platform fingerprint directory, and the SDK selection
# for the engine fingerprint, which must equal MAIN's (same commit, same engine
# inputs). Refuses when the fingerprint has no retained SDK in MAIN, so a
# command in the copy can never start an SDK preparation for it.
# Retire with: bash copy.sh --remove MAIN COPY
set -euo pipefail
if [ "${1:-}" = --remove ]; then
  MAIN=$2; COPY=$3
  [ -x "$COPY/bin/bl" ] && (cd "$COPY" && BL_SDK_LOCK_WAIT=0 ./bin/bl realm stop >/dev/null 2>&1 || true)
  # The client's per-tree generation service outlives the VM; stop it too.
  pkill -f "[g]eneration-service $COPY\$" || true
  git -C "$MAIN" worktree remove --force "$COPY"
  exit 0
fi
MAIN=$1; COPY=$2; REV=${3:-HEAD}
[ ! -e "$COPY" ] || { echo "copy.sh: $COPY exists" >&2; exit 64; }
git -C "$MAIN" worktree add --detach "$COPY" "$REV" >/dev/null 2>&1
fp=$(python3 "$COPY/scripts/sdk-inputs" --root "$COPY")
src="$MAIN/.bl/sdks/$fp"
[ -L "$src/result-sdk" ] && [ -L "$src/source-engine" ] || {
  echo "copy.sh: MAIN has no retained SDK for engine fingerprint $fp; prepare MAIN first" >&2; exit 69; }
mkdir -p "$COPY/.bl/sdks/$fp" "$COPY/.bl/platforms"
cp -P "$src/result-sdk" "$src/source-engine" "$COPY/.bl/sdks/$fp/"
ln -s "$(readlink -f "$src/result-sdk")" "$COPY/.bl/sdks/current-sdk"
platform_fp=$(head -1 "$MAIN/.bl/platform-stat.v1")
platform=$(readlink -f "$MAIN/.bl/platforms/$platform_fp")
ln -s "$platform" "$COPY/.bl/platforms/$platform_fp"
ln -s "$platform" "$COPY/.bl/checkout-platform"
echo "engine $fp sdk $(readlink -f "$src/result-sdk") platform $platform"
