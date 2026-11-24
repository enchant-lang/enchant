set -u
MAIN=/home/othman/code/undefine/beam-lisp--execution-protocol
WT=$MAIN/.claude/worktrees/lane-warm3
export BL_SDK_REUSE_CURRENT=1
cd /tmp/w3-othman/proj
mkdir -p $MAIN/.bl/bin
[ -e $MAIN/.bl/bin/bl ] && { echo "entry exists, abort"; ls -la $MAIN/.bl/bin; exit 1; }
ln -s $WT/.cargo-target/release/drop-launcher $MAIN/.bl/bin/bl
echo "== by path"; $MAIN/.bl/bin/bl run /tmp/w3-othman/one.bl; echo rc=$?
echo "== argv"; $MAIN/.bl/bin/bl eval '(println (BeamLisp/argv))' -- a b; echo rc=$?
echo "== via PATH"; PATH=$MAIN/.bl/bin:$PATH bl run /tmp/w3-othman/one.bl; echo rc=$?
echo "== preset platform goes through bin/bl"; BL_CHECKOUT_PLATFORM=$(readlink -f $MAIN/.bl/checkout-platform) $MAIN/.bl/bin/bl run /tmp/w3-othman/one.bl; echo rc=$?
echo "== relative"; cd $MAIN && ./.bl/bin/bl run /tmp/w3-othman/one.bl; echo rc=$?; cd /tmp/w3-othman/proj
rm $MAIN/.bl/bin/bl; rmdir $MAIN/.bl/bin
ls $MAIN/.bl/bin 2>&1 | head -1
