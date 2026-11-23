set -u
R=/tmp/u9root
P=/nix/store/p97z1g0hbvqd8jfmk3cxmk1z8fczk8hh-beam-lisp-checkout-platform
export BL_CHECKOUT_PLATFORM=$P
export BL_SDK_REUSE_CURRENT=1
cd $R
flock -x $R/.bl/sdks/preparation.lock -c "sleep 2400" &
H=$!; sleep 1
mkdir -p /tmp/u9/out
echo "LOAD-BEFORE"; uptime; nproc
./bin/bl realm stop >/dev/null 2>&1
./bin/bl run /tmp/u9/one.bl >/dev/null 2>&1   # start/warm
./bin/bl run /tmp/u9/one.bl >/dev/null 2>&1
nano() { date +%s%N; }
t() { local a b; a=$(nano); "$@" >/dev/null 2>&1; b=$(nano); echo $(( (b-a)/1000 )); }
echo "=== checkout warm unmarked 20 (us)"
for i in $(seq 20); do t ./bin/bl run /tmp/u9/one.bl; done > /tmp/u9/out/checkout-warm.us
tr '\n' ' ' < /tmp/u9/out/checkout-warm.us; echo
echo "=== checkout warm marked 20 (us)"
for i in $(seq 20); do U9_MARKS=1 U9_MARKS_FILE=/tmp/u9/out/marks-$i.log t ./bin/bl run /tmp/u9/one.bl; done > /tmp/u9/out/checkout-warm-marked.us
tr '\n' ' ' < /tmp/u9/out/checkout-warm-marked.us; echo
echo "=== checkout changed-file 20 (us)"
for i in $(seq 20); do echo "(println $i)" > /tmp/u9/one.bl; t ./bin/bl run /tmp/u9/one.bl; done > /tmp/u9/out/checkout-changed.us
tr '\n' ' ' < /tmp/u9/out/checkout-changed.us; echo
echo "" > /tmp/u9/one.bl; echo '(println 1)' > /tmp/u9/one.bl
echo "=== /bin/true 20 (us)"; for i in $(seq 20); do t /bin/true; done > /tmp/u9/out/true.us; tr '\n' ' ' < /tmp/u9/out/true.us; echo
echo "=== which via checkout 20 (us)"; for i in $(seq 20); do t ./bin/bl which; done > /tmp/u9/out/which.us; tr '\n' ' ' < /tmp/u9/out/which.us; echo
echo "=== engine-inputs 20 (us)"; for i in $(seq 20); do t $P/bin/drop-launcher --engine-inputs $R; done > /tmp/u9/out/engine-inputs.us; tr '\n' ' ' < /tmp/u9/out/engine-inputs.us; echo
echo "=== digest cache off 20 (us)"
for i in $(seq 20); do a=$(nano); BL_CHECKOUT_DIGEST_CACHE=0 ./bin/bl run /tmp/u9/one.bl >/dev/null 2>&1; b=$(nano); echo $(( (b-a)/1000 )); done > /tmp/u9/out/checkout-warm-nocache.us
tr '\n' ' ' < /tmp/u9/out/checkout-warm-nocache.us; echo
echo "=== installed drop warm 20 (us)"
B=/etc/profiles/per-user/othman/bin/bl
mkdir -p /tmp/u9proj; printf '{:name "u9proj"}\n' > /tmp/u9proj/env.bl; echo '(println 1)' > /tmp/u9proj/one.bl
cd /tmp/u9proj
$B realm stop >/dev/null 2>&1; $B realm start --root /tmp/u9proj >/dev/null 2>&1; $B run /tmp/u9proj/one.bl >/dev/null 2>&1; $B run /tmp/u9proj/one.bl >/dev/null 2>&1
for i in $(seq 20); do t $B run /tmp/u9proj/one.bl; done > /tmp/u9/out/installed-warm.us
tr '\n' ' ' < /tmp/u9/out/installed-warm.us; echo
$B realm stop >/dev/null 2>&1
cd $R
echo "=== strace checkout warm"
strace -f -tt -e trace=execve,connect,write,read,exit_group -o /tmp/u9/out/strace-checkout.txt ./bin/bl run /tmp/u9/one.bl > /tmp/u9/out/strace-run.out 2>&1
echo "strace exit $? lines $(wc -l < /tmp/u9/out/strace-checkout.txt)"; head -3 /tmp/u9/out/strace-run.out
echo "LOAD-AFTER"; uptime
kill $H 2>/dev/null
