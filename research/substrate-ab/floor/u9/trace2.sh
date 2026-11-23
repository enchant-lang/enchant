set -u
R=/tmp/u9root
P=/nix/store/p97z1g0hbvqd8jfmk3cxmk1z8fczk8hh-beam-lisp-checkout-platform
export BL_CHECKOUT_PLATFORM=$P
export BL_SDK_REUSE_CURRENT=1
cd $R
flock -x $R/.bl/sdks/preparation.lock -c "sleep 2400" &
H=$!; sleep 1
for f in /run/user/1000/beam_lisp/*.meta; do
  if grep -qa u9root "$f" 2>/dev/null; then
    sock=${f%.meta}.sock
    pid=$(ss -xlp 2>/dev/null | grep "$sock" | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
    [ -n "${pid:-}" ] && kill "$pid" 2>/dev/null
  fi
done
sleep 2
./bin/bl run /tmp/u9/one.bl >/tmp/u9/out/precheck.txt 2>&1
grep -q '^1$' /tmp/u9/out/precheck.txt || { echo PRECHECK-FAILED; cat /tmp/u9/out/precheck.txt; kill $H; exit 1; }
./bin/bl run /tmp/u9/one.bl >/dev/null 2>&1
echo "=== reload probe (source changed)"
./bin/bl run /tmp/u9/load_all.bl 2>&1 | tail -1
echo "=== wall unchanged"
U9_OUT=/tmp/u9/out/wall2-unchanged.txt ./bin/bl run /tmp/u9/start_wall2.bl 2>&1 | tail -1
for i in $(seq 20); do ./bin/bl run /tmp/u9/one.bl >/dev/null 2>&1; done
U9_OUT=/tmp/u9/out/wall2-unchanged.txt ./bin/bl run /tmp/u9/stop_wall.bl >/dev/null 2>&1
head -12 /tmp/u9/out/wall-unchanged.txt | cut -c1-160

echo "=== sampler (focused)"
./bin/bl run /tmp/u9/start_sampler.bl >/dev/null 2>&1
a=$(date +%s%N); for i in $(seq 20); do ./bin/bl run /tmp/u9/one.bl >/dev/null 2>&1; done; b=$(date +%s%N)
U9_OUT=/tmp/u9/out/samples2.txt ./bin/bl run /tmp/u9/stop_sampler.bl >/dev/null 2>&1
echo "window us $(( (b-a)/1000 ))"; head -20 /tmp/u9/out/samples2.txt | cut -c1-140
uptime
kill $H 2>/dev/null
