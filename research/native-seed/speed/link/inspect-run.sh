#!/usr/bin/env bash
# Focused inspection runner: pinned SDK, cwd = main checkout (read-only closure
# sources whose SHAs the partition pins), BL sources from the link worktree.
set -euo pipefail
wt=/home/othman/.claude/jobs/bbc0cb7e/tmp/wt-link/research/native-seed
main=/home/othman/.claude/jobs/bbc0cb7e/tmp/link-out/cwd
sdk=/nix/store/a83cfqc60h151907z27h2iic6rrz05id-beam-lisp-sdk-selection
src=/nix/store/br0d0abczvbv0rqivpr533a5a0jd1zxq-source
runtime=$(mktemp -d /tmp/bl-link-inspect-XXXXXXXX)
systemd-run --user --quiet --collect --wait --pipe \
  --working-directory="$main" --property=MemoryMax=3G --property=MemorySwapMax=0 \
  --property=RuntimeMaxSec=240 --property=KillMode=control-group \
  --setenv=XDG_RUNTIME_DIR="$runtime" \
  "$sdk/bin/bl" --cold -p "$wt/src" -p "$src/priv/build" "$@"
rm -rf -- "$runtime"
