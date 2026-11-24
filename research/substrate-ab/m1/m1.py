#!/usr/bin/env python3
"""M1: what a user waits for when editing a real project (Enchant, this repo).

Usage (from anywhere; every path is explicit):

    python3 -I m1.py --checkout CHECKOUT --out OUT [--cycles 5] [--probe none|sampler|trace]
                     [--setup-only] [--cold N]

CHECKOUT is a private copy of the Enchant checkout (a `git worktree add` of
main), never the user's checkout: this script edits files in it. It serves as
both the project and the engine checkout, so its warm VM is this script's own
and a `realm stop` here touches no one else's VM. `setup` (always run) adds a
small macro provider fixture and a probe file to it; `--setup-only` stops there.

Each cycle: `realm stop`; the first command in the fresh VM; warm unchanged
commands; four body edits of `scene-demo.frame-plan` (the first, then repeats);
two edits of the macro provider `scene-demo.m1-guard`, which `frame-plan` and
`film` expand; three edits of `priv/lib/scene/core.bl` `fail` (the U15
overlay); then every file is restored and the SDK's code is checked again.
Every edit is verified by output, not assumed: the probe prints the edited
message and the macro's value in both dependents.

Timed command wall clock is from just before the file is saved to the exit of
the command, with `BL_CHECKOUT_PHASE_TIMES=1` so the client's own phases are
recorded too. `--probe sampler|trace` loads `m1_sampler.erl` or `m1_trace.erl`
into the VM after the first command; those runs are for attribution, not for
timing. Results: OUT/records.jsonl (one row per command), OUT/summary.json.
"""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent

PLAN = "examples/scene-renderer/scene_demo/frame_plan.bl"
FILM = "examples/scene-renderer/scene_demo/film.bl"
GUARD = "examples/scene-renderer/scene_demo/m1_guard.bl"
CORE = "priv/lib/scene/core.bl"
PROBE = "m1_probe.bl"

RUN_HELLO = ["run", "examples/hello.bl"]
RUN_PROBE = ["run", PROBE]
TEST_PLAN = ["test", "test/bl/scene/frame_plan_test.bl"]
CHECK_PLAN = ["check", PLAN]

GUARD_SRC = """(ns scene-demo.m1-guard)
;; M1 fixture: a project macro provider with two project dependents
;; (scene-demo.frame-plan and scene-demo.film). Edited by research/substrate-ab/m1/m1.py.
(defmacro mark [] "M1-MACRO-0")
(defmacro within? [x lo hi] `(let [v# ~x] (and (int? v#) (<= ~lo v#) (< v# ~hi))))
"""
PROBE_SRC = """(ns m1-probe (:require [scene-demo.frame-plan :as plan] [scene-demo.film :as film]))
(println "M1-PROBE"
         (try (plan/selection ["out" "bogus"] 10 [0]) (catch e (ex-message e)))
         (plan/m1-mark) (film/m1-mark))
"""
BODY_NEEDLE = '"Choose review or film"'
MACRO_NEEDLE = '"M1-MACRO-0"'
CORE_NEEDLE = "(defn fail [message data] (throw (ex-info message data)))"


def body_edit(k):
    return f'"Choose review or film #{k}"'


def macro_edit(k):
    return f'"M1-MACRO-{k}"'


def core_edit(k):
    return f'(defn fail [message data] (throw (ex-info (str "L{k}: " message) data)))'


def setup(root):
    """Add the fixture to the private copy. Idempotent."""
    plan = root / PLAN
    text = plan.read_text()
    if "m1-guard" not in text:
        text = text.replace("(ns scene-demo.frame-plan (:require [scene.core :as scene]))",
                            "(ns scene-demo.frame-plan (:require [scene.core :as scene] [scene-demo.m1-guard :as guard]))")
        text = text.replace("(every? #(and (int? %) (<= 0 %) (< % total)) indices)",
                            "(every? #(guard/within? % 0 total) indices)")
        text += "\n(defn m1-mark [] (guard/mark))\n"
        assert "guard/within?" in text and "m1-guard" in text, "frame_plan.bl changed shape"
        plan.write_text(text)
    film = root / FILM
    text = film.read_text()
    if "m1-guard" not in text:
        text = text.replace("(ns scene-demo.film (:require [scene.core :as s]))",
                            "(ns scene-demo.film (:require [scene.core :as s] [scene-demo.m1-guard :as guard]))")
        text += "\n(defn m1-mark [] (guard/mark))\n"
        assert "m1-guard" in text, "film.bl changed shape"
        film.write_text(text)
    (root / GUARD).write_text(GUARD_SRC)
    (root / PROBE).write_text(PROBE_SRC)
    for rel, needle in ((PLAN, BODY_NEEDLE), (GUARD, MACRO_NEEDLE), (CORE, CORE_NEEDLE)):
        assert needle in (root / rel).read_text(), f"{rel} lacks {needle}"


def loadavg():
    return Path("/proc/loadavg").read_text().split()[:3]


def vm_pids(root):
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if not os.readlink(entry / "exe").endswith("beam.smp"):
                continue
            environ = (entry / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        if f"BL_CHECKOUT_ROOT={root}".encode() in environ:
            found.append(int(entry.name))
    return sorted(found)


def rss_mb(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024
    except OSError:
        return None
    return None


class Bench:
    def __init__(self, root, out, probe):
        self.root = root
        self.out = out
        self.probe = probe
        self.label_file = out / "window"
        self.records = open(out / "records.jsonl", "a")
        self.bl = str(root / "bin/bl")
        self.direct = str(root / ".bl/bin/bl")
        self.env = dict(os.environ, BL_CHECKOUT_PHASE_TIMES="1", BL_SDK_LOCK_WAIT="0")
        # Never select a stale SDK silently, and never queue behind a build.
        self.env.pop("BL_SDK_REUSE_CURRENT", None)

    def window(self, label):
        tmp = self.label_file.with_suffix(".tmp")
        tmp.write_text(label + "\n")
        tmp.replace(self.label_file)

    def timed(self, case, argv, *, cycle, before=None, expect=None, entry=None, cold=False):
        """Run one command; `before` (the save) runs inside the timed span."""
        exe = entry or self.bl
        args = [exe] + (["--cold"] if cold else []) + argv
        self.window(f"c{cycle}/{case}")
        load = loadavg()
        started = time.monotonic()
        if before:
            before()
        result = subprocess.run(args, cwd=self.root, env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, timeout=900)
        wall = (time.monotonic() - started) * 1000
        self.window("idle")
        phases = {}
        for line in result.stderr.splitlines():
            m = re.match(r"U10-PHASE (\S+) (\d+)$", line)
            if m:
                phases[m.group(1)] = phases.get(m.group(1), 0) + int(m.group(2))
        stderr = "\n".join(l for l in result.stderr.splitlines() if not l.startswith("U10-PHASE"))
        ok = result.returncode == 0
        seen = None
        if expect is not None:
            seen = all(e in result.stdout for e in expect)
            ok = ok and seen
        row = {"cycle": cycle, "case": case, "argv": argv, "entry": Path(exe).name if entry else "bin/bl",
               "cold": cold, "wall_ms": round(wall, 2), "rc": result.returncode, "ok": ok, "expect": expect,
               "seen": seen, "client_us": phases, "load": load, "probe": self.probe,
               "stdout_tail": result.stdout.strip().splitlines()[-3:], "stderr_tail": stderr.strip().splitlines()[-6:]}
        self.records.write(json.dumps(row) + "\n")
        self.records.flush()
        flag = "" if ok else "  <-- NOT OK"
        print(f"c{cycle} {case:32s} {wall:9.1f} ms rc={result.returncode} client={phases.get('total', '-')}us load={load[0]}{flag}",
              flush=True)
        if not ok:
            print("   stdout: " + " | ".join(row["stdout_tail"]) + "\n   stderr: " + " | ".join(row["stderr_tail"]), flush=True)
        return row

    def untimed(self, argv):
        return subprocess.run([self.bl] + argv, cwd=self.root, env=self.env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=900)

    def stop(self, cycle):
        started = time.monotonic()
        r = self.untimed(["realm", "stop"])
        ms = (time.monotonic() - started) * 1000
        print(f"c{cycle} realm stop {ms:.0f} ms rc={r.returncode} vms={vm_pids(self.root)}", flush=True)

    def replace(self, rel, old, new):
        path = self.root / rel
        def save():
            text = path.read_text()
            assert old in text, f"{rel}: {old!r} not found"
            path.write_text(text.replace(old, new, 1))
        return save

    def start_probe(self, cycle):
        if self.probe == "none":
            return
        beams = self.out / "beams"
        beams.mkdir(exist_ok=True)
        env = dict(self.env, M1_DIR=str(HERE), M1_BEAM_DIR=str(beams), M1_LABEL_FILE=str(self.label_file),
                   M1_PROBE=self.probe)
        r = subprocess.run([self.bl, "run", str(HERE / "load_probes.bl")], cwd=self.root, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=900)
        print(f"c{cycle} probe start: {r.stdout.strip().splitlines()[-1:]}", flush=True)

    def stop_probe(self, cycle):
        if self.probe == "none":
            return
        env = dict(self.env, M1_PROBE=self.probe, M1_PROFILE_OUT=str(self.out / f"profile-{self.probe}-c{cycle}.txt"))
        r = subprocess.run([self.bl, "run", str(HERE / "stop_probes.bl")], cwd=self.root, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=900)
        print(f"c{cycle} probe stop: {r.stdout.strip().splitlines()[-1:]}", flush=True)


def cycle(b, c):
    root = b.root
    originals = {rel: (root / rel).read_bytes() for rel in (PLAN, GUARD, CORE)}
    b.stop(c)
    try:
        # 4. Cold, as a user meets it: the first command after the VM stopped.
        b.timed("first-in-fresh-vm/test", TEST_PLAN, cycle=c)
        vm = vm_pids(root)
        b.start_probe(c)
        # 1. Warm, unchanged.
        for i in range(3):
            b.timed("warm/test", TEST_PLAN, cycle=c)
            b.timed("warm/run-hello", RUN_HELLO, cycle=c)
            b.timed("warm/run-probe", RUN_PROBE, cycle=c, expect=['Choose review or film', "M1-MACRO-0 M1-MACRO-0"])
            b.timed("warm/check", CHECK_PLAN, cycle=c)
            b.timed("warm/run-hello/direct", RUN_HELLO, cycle=c, entry=b.direct)
            b.timed("warm/test/direct", TEST_PLAN, cycle=c, entry=b.direct)
        # 2. Body edits of scene-demo.frame-plan.
        prev = BODY_NEEDLE
        for k, (case, argv) in enumerate([("body/first/test", TEST_PLAN), ("body/repeat/run-probe", RUN_PROBE),
                                          ("body/repeat/run-probe", RUN_PROBE), ("body/repeat/test", TEST_PLAN)], 1):
            new = body_edit(f"{c}.{k}")
            expect = [f"film #{c}.{k}"] if argv is RUN_PROBE else None
            b.timed(case, argv, cycle=c, before=b.replace(PLAN, prev, new), expect=expect)
            b.timed("body/after/run-probe", RUN_PROBE, cycle=c, expect=[f"film #{c}.{k}"])
            prev = new
        # 3. Macro provider edits: both dependents must show the new expansion.
        prevm = MACRO_NEEDLE
        for k, (case, argv) in enumerate([("macro/first/run-probe", RUN_PROBE), ("macro/repeat/test", TEST_PLAN),
                                          ("macro/repeat/run-probe", RUN_PROBE)], 1):
            tag = f"M1-MACRO-{c}{k}"
            new = f'"{tag}"'
            expect = [f"{tag} {tag}"] if argv is RUN_PROBE else None
            b.timed(case, argv, cycle=c, before=b.replace(GUARD, prevm, new), expect=expect)
            b.timed("macro/after/run-probe", RUN_PROBE, cycle=c, expect=[f"{tag} {tag}"])
            prevm = new
        # 5. A priv/lib edit (U15 overlay) seen from the project.
        prevl = CORE_NEEDLE
        for k, (case, argv) in enumerate([("lib/first/run-probe", RUN_PROBE), ("lib/repeat/run-probe", RUN_PROBE),
                                          ("lib/repeat/test", TEST_PLAN)], 1):
            new = core_edit(f"{c}.{k}")
            expect = [f"L{c}.{k}: Choose"] if argv is RUN_PROBE else None
            b.timed(case, argv, cycle=c, before=b.replace(CORE, prevl, new), expect=expect)
            b.timed("lib/after/run-probe", RUN_PROBE, cycle=c, expect=[f"L{c}.{k}: Choose"])
            prevl = new
        # Revert everything; the SDK's scene.core answers again.
        def revert():
            for rel, data in originals.items():
                (root / rel).write_bytes(data)
        b.timed("revert/run-probe", RUN_PROBE, cycle=c, before=revert,
                expect=["M1-PROBE Choose review or film M1-MACRO-0 M1-MACRO-0"])
        b.stop_probe(c)
        same = vm_pids(root) == vm
        print(f"c{c} same VM throughout: {same} {vm} rss={[rss_mb(p) for p in vm]} MB", flush=True)
        b.records.write(json.dumps({"cycle": c, "case": "vm", "same_vm": same, "pids": vm,
                                    "rss_mb": [rss_mb(p) for p in vm]}) + "\n")
    finally:
        for rel, data in originals.items():
            (root / rel).write_bytes(data)


def cold(b, n):
    b.stop("cold")
    for i in range(n):
        b.timed("cold/run-hello", RUN_HELLO, cycle="cold", cold=True)
        b.timed("cold/test", TEST_PLAN, cycle="cold", cold=True)


def summarize(out):
    rows = [json.loads(l) for l in open(out / "records.jsonl") if l.strip()]
    groups = {}
    for r in rows:
        if "wall_ms" not in r:
            continue
        groups.setdefault(r["case"], []).append(r)

    def stats(xs):
        xs = sorted(xs)
        q = lambda f: xs[min(len(xs) - 1, int(f * len(xs)))]
        return {"n": len(xs), "median": round(statistics.median(xs), 1), "min": round(xs[0], 1),
                "p25": round(q(0.25), 1), "p75": round(q(0.75), 1), "max": round(xs[-1], 1)}

    summary = {}
    for case, rs in sorted(groups.items()):
        walls = [r["wall_ms"] for r in rs if r["ok"]]
        client = [r["client_us"].get("total", 0) / 1000 for r in rs if r["ok"] and r["client_us"]]
        summary[case] = {"wall_ms": stats(walls) if walls else None,
                         "client_before_exec_ms": stats(client) if client else None,
                         "failed": sum(1 for r in rs if not r["ok"]),
                         "load_1m": [float(r["load"][0]) for r in rs]}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    for case, s in summary.items():
        w = s["wall_ms"]
        if w:
            print(f"{case:34s} n={w['n']:3d} median={w['median']:8.1f} min={w['min']:8.1f} max={w['max']:8.1f}"
                  f" client={s['client_before_exec_ms']['median'] if s['client_before_exec_ms'] else '-'} failed={s['failed']}")
        else:
            print(f"{case:34s} all failed ({s['failed']})")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--cycles", type=int, default=5)
    ap.add_argument("--cold", type=int, default=0)
    ap.add_argument("--probe", default="none", choices=["none", "sampler", "trace"])
    ap.add_argument("--setup-only", action="store_true")
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    root = a.checkout.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.summary_only:
        summarize(a.out)
        return 0
    assert root != Path("/home/othman/code/undefine/beam-lisp--execution-protocol"), "never the user's checkout"
    setup(root)
    if a.setup_only:
        return 0
    b = Bench(root, a.out, a.probe)
    print(f"START {time.strftime('%FT%T')} load {loadavg()} sdk {os.path.realpath(root / '.bl/sdks/current-sdk')}", flush=True)
    try:
        for c in range(1, a.cycles + 1):
            cycle(b, c)
        if a.cold:
            cold(b, a.cold)
    finally:
        b.stop("end")
    print(f"END {time.strftime('%FT%T')} load {loadavg()} sdk {os.path.realpath(root / '.bl/sdks/current-sdk')}", flush=True)
    summarize(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
