# usage: bash measure.sh LABEL BL [CLIENT_ONLY_PLATFORM_FROM]
set -u
LABEL=$1; BL=$2; N=${N:-15}
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
O=/tmp/f1-othman/out/$LABEL; mkdir -p $O
export BL_SDK_REUSE_CURRENT=1
cd /tmp/f1-othman/proj
us() { local a=${EPOCHREALTIME/./} ; "$@" >/dev/null 2>&1; local b=${EPOCHREALTIME/./}; echo $((b-a)); }
loop() { local f=$1; shift; : > $O/$f; for i in $(seq $N); do us "$@" >> $O/$f; done; }
echo "LOAD-BEFORE $(uptime)"
$BL run one.bl; $BL run one.bl
loop true.us /bin/true
loop bl-run.us $BL run one.bl
if [ -n "${CLIENT:-}" ]; then
  ( P=$($MAIN/scripts/prepare-checkout-platform); P=$(readlink -f $P)
    export BL_CHECKOUT_ROOT=$MAIN BL_CHECKOUT_PLATFORM=$P BL_ARTIFACT_PLATFORM=$P/artifact-platform
    export BL_PREPARED_NATIVES=$(readlink -f $P/native-products) BL_BIN=$P/bin/drop-launcher PATH=$P/bin:$PATH
    [ "$CLIENT" = platform ] && CLIENT=$P/bin/drop-launcher
    echo "CLIENT $CLIENT"
    loop client-run.us $CLIENT --checkout $MAIN -- run one.bl
    BL_CHECKOUT_PHASE_TIMES=1 $CLIENT --checkout $MAIN -- run one.bl 2>&1 | grep U10-PHASE | tr '\n' ' '; echo )
fi
if [ -n "${NOEXEC:-}" ]; then loop shell-noexec.us sh $NOEXEC run one.bl; loop platform-script.us $MAIN/scripts/prepare-checkout-platform; fi
loop bl-run2.us $BL run one.bl
echo "LOAD-AFTER $(uptime)"
python3 -I /tmp/f1-othman/scripts/stats.py $O/*.us
