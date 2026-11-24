set -u
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
I=$MAIN/.claude/worktrees/integration
T=/tmp/w3-othman
med(){ sort -n | awk '{a[NR]=$1} END{print a[int((NR+1)/2)], "min", a[1], "max", a[NR]}'; }
gl(){ echo "gate-style $1: median $(for i in $(seq 1 21); do t=$(date +%s%N); $2 run $T/one.bl >/dev/null 2>&1; echo $(( ($(date +%s%N)-t)/1000000 )); done | med) ms"; }
us(){ echo "epoch-style $1: median $(for i in $(seq 1 21); do a=${EPOCHREALTIME/./}; $2 run $T/one.bl >/dev/null 2>&1; b=${EPOCHREALTIME/./}; echo $((b-a)); done | med) us"; }
uptime
for r in 1 2; do
cd $I; gl introot ./bin/bl; us introot ./bin/bl
cd $T/proj-int; gl intproj $I/bin/bl; us intproj $I/bin/bl
done
uptime
