set -u
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
export BL_SDK_REUSE_CURRENT=1
cd /tmp/w3-othman/proj
C=$(readlink -f $MAIN/.bl/checkout-platform/bin/drop-launcher)
med(){ sort -n | awk '{a[NR]=$1} END{print a[int((NR+1)/2)], "min", a[1], "max", a[NR]}'; }
us(){ echo "$1: $(for i in $(seq 1 31); do a=${EPOCHREALTIME/./}; "${@:2}" >/dev/null 2>&1; b=${EPOCHREALTIME/./}; echo $((b-a)); done | med) us"; }
uptime
$MAIN/bin/bl run /tmp/w3-othman/one.bl >/dev/null
us true /bin/true
us sh-true sh -c true
us launcher-noargs $C --nonexistent-flag
us binbl $MAIN/bin/bl run /tmp/w3-othman/one.bl
us direct $C --checkout $MAIN -- run /tmp/w3-othman/one.bl
us binbl $MAIN/bin/bl run /tmp/w3-othman/one.bl
us direct $C --checkout $MAIN -- run /tmp/w3-othman/one.bl
uptime
