set -u
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
WT=$MAIN/.claude/worktrees/lane-warm-floor
NEWP=$(cat /tmp/f1-othman/newp)
OLDP=/nix/store/ld6jjq7gb58dvnfh3sd606pycsch6f6b-beam-lisp-checkout-platform
S=/tmp/f1-othman/ns; FP=474a3584d31bdc6322dfe86c2d15238e95a218388017dc05868e10f2b7463896
echo "ID $(id -u)"
BL=/tmp/f1-othman/scripts/bl-new
echo "BIN-BL-IS-NEW $(grep -c checkout-platform/bin/drop-launcher $BL) MAIN-BIN-BL-NEW $(grep -c checkout-platform/bin/drop-launcher $MAIN/bin/bl)"
sed 's|^case "\$0".*|HERE=/home/othman/code/undefine/beam-lisp--execution-protocol/bin|; 0,/^  exec "\$CLIENT"/s|^  exec "\$CLIENT".*|  exit 0|' $WT/bin/bl > /tmp/f1-othman/scripts/bl-noexec-new
export BL_SDK_REUSE_CURRENT=1
cd /tmp/f1-othman/proj
check() { local label=$1; shift; out=$("$@" 2>&1); echo "CHECK $label exit=$? out=$(echo "$out" | tail -2 | tr '\n' '|')"; }
check new-first $BL run one.bl
check new-second $BL run one.bl
echo "POINTER $(readlink $MAIN/.bl/checkout-platform)"
N=15 NOEXEC= CLIENT= bash /tmp/f1-othman/scripts/measure.sh new $BL
O=/tmp/f1-othman/out/new
us() { local a=${EPOCHREALTIME/./} ; "$@" >/dev/null 2>&1; local b=${EPOCHREALTIME/./}; echo $((b-a)); }
: > $O/shell-noexec-new.us; for i in $(seq 15); do us sh /tmp/f1-othman/scripts/bl-noexec-new run one.bl >> $O/shell-noexec-new.us; done
for i in 1 2 3; do BL_CHECKOUT_PHASE_TIMES=1 $BL run one.bl 2>&1 | grep U10-PHASE | tr '\n' ' '; echo; done
python3 -I /tmp/f1-othman/scripts/stats.py $O/shell-noexec-new.us
check preset env BL_CHECKOUT_PLATFORM=$NEWP $BL run one.bl
check digest-cache-off env BL_CHECKOUT_DIGEST_CACHE=0 $BL run one.bl
check cold $BL --cold run one.bl
echo "--- other-binary: the selected platform is main's ($OLDP)"
ln -sfn $OLDP $S/dotbl/platforms/$FP
check other-first $BL run one.bl
check other-second $BL run one.bl
echo "POINTER $(readlink $MAIN/.bl/checkout-platform) (old client records nothing)"
: > $O/other-binary.us; for i in $(seq 15); do us $BL run one.bl >> $O/other-binary.us; done
python3 -I /tmp/f1-othman/scripts/stats.py $O/other-binary.us
ln -sfn $NEWP $S/dotbl/platforms/$FP
echo "--- no pointer: bin/bl runs the script once, the selected client records itself"
rm -f $MAIN/.bl/checkout-platform
check no-pointer $BL run one.bl
echo "POINTER $(readlink $MAIN/.bl/checkout-platform)"
echo "V1-FIRST-DIR-LINE $(grep -m1 '^d' $MAIN/.bl/platform-stat.v1)"
check after-pointer $BL run one.bl
$BL realm stop
