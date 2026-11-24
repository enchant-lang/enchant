# M3 inner-loop gate: checkout_transport.py, warm_cancel.py and
# realm_stop_after_overlay.py (strict) through the branch's client binary, on a
# private copy (research/substrate-ab/m1/copy.sh) running main's SDK.
#   usage: bash gate.sh OUT   (M3_COPY, M3_CLIENT, M3_WRAP override the defaults)
# M3_WRAP is a directory holding bin/bl = wrap-bl. realm_stop_after_overlay.py
# runs as a copy with ROOT = the copy and BL = the wrapper.
WT=$(cd "$(dirname "$0")/../../.." && pwd)
COPY=${M3_COPY:-/tmp/m3-$USER/enchant}
WRAP=${M3_WRAP:-/tmp/m3-$USER/wrap}
export M3_COPY=$COPY M3_CLIENT=${M3_CLIENT:-$WT/.cargo-target/release/drop-launcher}
OUT=${1:?OUT}; mkdir -p "$OUT" "$WRAP/bin"
cp "$WT/research/substrate-ab/m3/wrap-bl" "$WRAP/bin/bl"; chmod +x "$WRAP/bin/bl"
sed -e "s|^ROOT = Path(__file__).resolve().parents\[2\]|ROOT = Path(\"$COPY\")|" \
    -e "s|^BL = ROOT / \"bin/bl\"|BL = Path(\"$WRAP/bin/bl\")|" \
    "$WT/test/scripts/realm_stop_after_overlay.py" > "$OUT/rso.py"
cd "$COPY"
"$COPY/bin/bl" realm stop >/dev/null 2>&1
echo "client $M3_CLIENT"; uptime
python3 -I "$WT/test/scripts/checkout_transport.py" --root "$WRAP" > "$OUT/ct.log" 2>&1; echo "== checkout_transport exit $?"; tail -3 "$OUT/ct.log"
python3 -I "$WT/test/scripts/warm_cancel.py" --root "$WRAP" > "$OUT/wc.log" 2>&1; echo "== warm_cancel exit $?"; tail -12 "$OUT/wc.log"
python3 -I "$OUT/rso.py" > "$OUT/rso.log" 2>&1; echo "== realm_stop_after_overlay exit $?"; tail -6 "$OUT/rso.log"
"$COPY/bin/bl" realm stop >/dev/null 2>&1
uptime
