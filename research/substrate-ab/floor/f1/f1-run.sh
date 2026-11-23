MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
cd /tmp/f1-othman/proj
N=15 NOEXEC=/tmp/f1-othman/scripts/bl-noexec CLIENT=platform bash /tmp/f1-othman/scripts/measure.sh old1 $MAIN/bin/bl
BL_SDK_REUSE_CURRENT=1 $MAIN/bin/bl realm stop
FP=474a3584d31bdc6322dfe86c2d15238e95a218388017dc05868e10f2b7463896; bash /tmp/f1-othman/scripts/newlisting.sh $MAIN $FP /tmp/f1-othman/ns/dotbl/platform-stat.v1
ln -sfn $(cat /tmp/f1-othman/newp) /tmp/f1-othman/ns/dotbl/checkout-platform
ln -sfn $(cat /tmp/f1-othman/newp) /tmp/f1-othman/ns/dotbl/platforms/$FP
sed 's|^case "\$0".*|HERE=/home/othman/code/undefine/beam-lisp--execution-protocol/bin|' $MAIN/.claude/worktrees/lane-warm-floor/bin/bl > /tmp/f1-othman/scripts/bl-new; chmod +x /tmp/f1-othman/scripts/bl-new
unshare -r -m bash /tmp/f1-othman/scripts/ns-mount.sh
N=15 NOEXEC= CLIENT= bash /tmp/f1-othman/scripts/measure.sh old2 $MAIN/bin/bl
BL_SDK_REUSE_CURRENT=1 $MAIN/bin/bl realm stop
for p in $(pgrep -f -- "$(readlink -f $(cat /tmp/f1-othman/newp)/bin/drop-launcher | sed 's/r$/[r]/')"); do echo "leftover $p $(tr '\0' ' ' < /proc/$p/cmdline | cut -c1-150)"; kill $p; done
scripts=/home/othman/code/undefine/beam-lisp--execution-protocol/scripts; $scripts/bl-mem 2>/dev/null | grep -i f1-othman || echo "no f1 VMs"
