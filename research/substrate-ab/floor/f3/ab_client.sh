set -u
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
WT=$MAIN/.claude/worktrees/lane-warm3
export BL_SDK_REUSE_CURRENT=1
cd /tmp/w3-othman/proj
P=$(readlink -f $MAIN/.bl/checkout-platform)
export BL_CHECKOUT_ROOT=$MAIN BL_CHECKOUT_PLATFORM=$P BL_ARTIFACT_PLATFORM=$P/artifact-platform
export BL_PREPARED_NATIVES=$(readlink -f $P/native-products) BL_BIN=$P/bin/drop-launcher PATH=$P/bin:$PATH
OLD=$P/bin/drop-launcher; NEW=$WT/.cargo-target/release/drop-launcher
for c in $OLD $NEW; do for i in 1 2 3; do $c --checkout $MAIN -- run /tmp/w3-othman/one.bl >/dev/null 2>&1; done; done
$NEW --checkout $MAIN -- run /tmp/w3-othman/one.bl; $NEW --checkout $MAIN -- eval '(System/get_env "HOME")'
uptime
: > /tmp/w3-othman/out/old.us; : > /tmp/w3-othman/out/new.us
for r in $(seq 30); do
  for c in old new; do B=$OLD; [ $c = new ] && B=$NEW
    a=${EPOCHREALTIME/./}; $B --checkout $MAIN -- run /tmp/w3-othman/one.bl >/dev/null 2>&1; b=${EPOCHREALTIME/./}; echo $((b-a)) >> /tmp/w3-othman/out/$c.us
  done
done
uptime
python3 -I /tmp/w3-othman/scripts/stats.py /tmp/w3-othman/out/old.us /tmp/w3-othman/out/new.us
