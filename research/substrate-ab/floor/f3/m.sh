# usage: bash m.sh LABEL [N]
set -u
LABEL=$1; N=${2:-15}
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
BL=${BL:-$MAIN/bin/bl}
O=/tmp/w3-othman/out/$LABEL; mkdir -p $O
export BL_SDK_REUSE_CURRENT=1
cd ${PROJ:-/tmp/w3-othman/proj}
us() { local a=${EPOCHREALTIME/./} ; "$@" >/dev/null 2>&1; local b=${EPOCHREALTIME/./}; echo $((b-a)); }
loop() { local f=$1; shift; : > $O/$f; for i in $(seq $N); do us "$@" >> $O/$f; done; }
echo "LOAD-BEFORE $(uptime)"
$BL run ${ONE:-one.bl}; $BL run ${ONE:-one.bl}
loop true.us /bin/true
loop bl-run.us $BL run ${ONE:-one.bl}
for i in 1 2 3; do BL_CHECKOUT_PHASE_TIMES=1 $BL run ${ONE:-one.bl} 2>&1 | grep U10-PHASE | tr '\n' ' '; echo; done
loop bl-run2.us $BL run ${ONE:-one.bl}
echo "LOAD-AFTER $(uptime)"
python3 -I /tmp/w3-othman/scripts/stats.py $O/*.us
