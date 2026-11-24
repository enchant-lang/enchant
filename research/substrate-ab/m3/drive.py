"""M3 phase driver: N pairs of (first command in a fresh warm VM, --cold), each
with the m3_trace boot tracer. usage: python3 -I drive.py COPY OUT N [trace|plain]"""
import json, os, re, subprocess, sys, time
from pathlib import Path
copy, out, n = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
mode = sys.argv[4] if len(sys.argv) > 4 else "trace"
out.mkdir(parents=True, exist_ok=True)
probe = Path(os.environ.get("M3_BEAMS", Path(__file__).resolve().parent))
argv = ["test", "test/bl/scene/frame_plan_test.bl"]
base = dict(os.environ, BL_CHECKOUT_PHASE_TIMES="1", BL_SDK_LOCK_WAIT="0")
base.pop("BL_SDK_REUSE_CURRENT", None)
rows = open(out / "rows.jsonl", "a")
def stop():
    subprocess.run([str(copy / "bin/bl"), "realm", "stop"], cwd=copy, env=base,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
def run(kind, i):
    env = dict(base, M3_TRACE_MIN_US=os.environ.get("M3_TRACE_MIN_US", "20000"))
    if mode in ("trace", "sample"):
        env["M3_TRACE_OUT"] = str(out / f"{kind}-{i}.trace")
        env["ERL_AFLAGS"] = f"-pa {probe} -s m3_trace start"
        if mode == "sample": env["M3_SAMPLE"] = "1"
    cmd = [str(copy / "bin/bl")] + (["--cold"] if kind == "cold" else []) + argv
    load = open("/proc/loadavg").read().split()[0]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=copy, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900)
    t1 = time.time()
    ph = {m.group(1): int(m.group(2)) for m in re.finditer(r"U10-PHASE (\S+) (\d+)", r.stderr)}
    row = {"kind": kind, "i": i, "t0_us": int(t0 * 1e6), "t1_us": int(t1 * 1e6), "wall_ms": round((t1 - t0) * 1000, 1),
           "rc": r.returncode, "ok": r.returncode == 0 and "all green" in r.stdout, "load": load, "client_us": ph,
           "stderr": [l for l in r.stderr.splitlines() if not l.startswith("U10")][-5:]}
    rows.write(json.dumps(row) + "\n"); rows.flush()
    print(kind, i, row["wall_ms"], "ok" if row["ok"] else "FAIL", "load", load, ph.get("total"), flush=True)
try:
    for i in range(1, n + 1):
        stop(); run("warm", i)
        stop(); run("cold", i)
finally:
    stop()
