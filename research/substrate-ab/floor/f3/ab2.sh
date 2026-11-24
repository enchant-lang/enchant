set -u
export ONE=/tmp/w3-othman/one.bl
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
INT=$MAIN/.claude/worktrees/integration
for r in 1 2; do
BL=$INT/bin/bl PROJ=$INT bash /tmp/w3-othman/scripts/m.sh introot-$r 15
BL=$INT/bin/bl PROJ=/tmp/w3-othman/proj-int bash /tmp/w3-othman/scripts/m.sh intproj-$r 15
done
