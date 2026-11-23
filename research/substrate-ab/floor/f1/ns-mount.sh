set -u
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
WT=$MAIN/.claude/worktrees/lane-warm-floor
mount --bind $MAIN/.bl /tmp/f1-othman/ns/realbl || exit 1
mount --bind /tmp/f1-othman/ns/dotbl $MAIN/.bl || exit 1
exec unshare --user --map-user=1000 --map-group=100 bash /tmp/f1-othman/scripts/ns.sh
