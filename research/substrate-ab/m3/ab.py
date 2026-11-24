"""M3 A/B: per round, the first command in a fresh VM through the old client
and through the new client (both invoked as `CLIENT --checkout COPY -- ARGV`
with the platform preset, exactly as bin/bl's one-exec path sets it), and a
`bin/bl --cold` of the same command. Order rotates per round.
usage: python3 -I ab.py COPY OUT ROUNDS OLD_CLIENT NEW_CLIENT"""
import json, os, re, subprocess, sys, time
from pathlib import Path
copy, out, n, old, new = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
out.mkdir(parents=True, exist_ok=True)
argv = ["test", "test/bl/scene/frame_plan_test.bl"]
plat = os.path.realpath(copy / ".bl/checkout-platform")
base = dict(os.environ, BL_CHECKOUT_PHASE_TIMES="1", BL_SDK_LOCK_WAIT="0")
base.pop("BL_SDK_REUSE_CURRENT", None)
preset = dict(base, BL_CHECKOUT_PLATFORM=plat, BL_ARTIFACT_PLATFORM=plat + "/artifact-platform",
              BL_PREPARED_NATIVES=os.path.realpath(plat + "/native-products"), BL_BIN=plat + "/bin/drop-launcher",
              PATH=plat + "/bin:" + base["PATH"])
rows = open(out / "rows.jsonl", "a")
def stop():
    subprocess.run([str(copy / "bin/bl"), "realm", "stop"], cwd=copy, env=base,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
def run(kind, i):
    if kind == "cold":
        cmd, env = [str(copy / "bin/bl"), "--cold"] + argv, base
    else:
        cmd, env = [old if kind == "warm-old" else new, "--checkout", str(copy), "--"] + argv, preset
    load = open("/proc/loadavg").read().split()[0]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=copy, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900)
    t1 = time.time()
    ph = {m.group(1): int(m.group(2)) for m in re.finditer(r"U10-PHASE (\S+) (\d+)", r.stderr)}
    row = {"kind": kind, "i": i, "wall_ms": round((t1 - t0) * 1000, 1), "rc": r.returncode,
           "ok": r.returncode == 0 and "all green" in r.stdout, "load": load, "client_us": ph,
           "stderr": [l for l in r.stderr.splitlines() if not l.startswith("U10")][-5:]}
    rows.write(json.dumps(row) + "\n"); rows.flush()
    print(kind, i, row["wall_ms"], "ok" if row["ok"] else "FAIL " + " | ".join(row["stderr"]), "load", load, flush=True)
kinds = ["warm-old", "warm-new", "cold"]
try:
    for i in range(1, n + 1):
        for k in kinds[i % 3:] + kinds[:i % 3]:
            stop(); run(k, i)
finally:
    stop()
import statistics
allr = [json.loads(l) for l in open(out / "rows.jsonl")]
for k in kinds:
    w = sorted(r["wall_ms"] for r in allr if r["kind"] == k and r["ok"])
    if w: print(k, "n", len(w), "median", statistics.median(w), "min", w[0], "max", w[-1])
