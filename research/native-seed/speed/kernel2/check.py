#!/usr/bin/env python3
"""KERNEL2 native semantic differential.

1. BEAM oracle (pinned SDK):
     research/native-seed/run run research/native-seed/speed/kernel2/oracle.bl -- research/native-seed/speed/kernel2/out
2. Emitted rt (pinned SDK, AOT link context, no kernel-override):
     research/native-seed/run run research/native-seed/speed/kernel2/emit-rt.bl -- PARTITION LEAVES RT.bl out/rt-new.scm
   and once more from the ORIGINAL rt.bl (git show HEAD~:priv/boot/rt.bl) into out/rt-base.scm.
3. python3 research/native-seed/speed/kernel2/check.py

Loads this worktree's host sources + host/host-kernel.scm + out/rt-SIDE.scm +
out/oracle.scm + check.scm in the pinned gsi, in slices (one process each),
for SIDE = base and new. Every rt row of `new` must equal BEAM, or else equal
`base` (a difference that compiled original rt.bl already has natively, i.e. a
leaf/BEAM difference, not a rewrite difference). Native-only exotic inputs
must answer identically on both sides. Templates must equal their leaf.
"""
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
OUT = HERE / "out"
HOST = ["host.scm", "host/host-values.scm", "host/host-leaves.scm", "host/host-lazy.scm",
        "host/host-extra.scm", "host/host-compiler.scm", "host/host-match.scm", "host/host-kernel.scm"]
SLICE = 2000
MIN_SLICE = 250
GSI = Path(json.loads((BASE / "toolchain-pin.json").read_text())["gambit"]) / "bin/gsi"
OBJ = re.compile(r"#<[^>]*>")


def program(side):
    path = OUT / f"run-{side}.scm"
    parts = [BASE / p for p in HOST] + [OUT / f"rt-{side}.scm", OUT / "oracle.scm", HERE / "check.scm"]
    path.write_text("\n".join(p.read_text() for p in parts) + "\n")
    return path


def run(path, env):
    result = subprocess.run(["timeout", "120", str(GSI), str(path)], cwd=OUT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode, result.stdout


def run_phase(path, side, env, retries):
    """One process. Interpreted gsi 4.9.5 dumps core inside its GC after enough
    calls (speed/kernel/RESULT.md); a slice that crashes WITHOUT reporting a
    failure is re-run as two halves, down to MIN_SLICE rows."""
    code, text = run(path, {**os.environ, "KERNEL2_SIDE": side, **env})
    crashed = code != 0 and "(FAIL" not in text and "KERNEL2_SLICE_PASS" not in text
    if crashed and env.get("KERNEL2_PHASE") == "oracle":
        lo, hi = int(env["KERNEL2_FROM"]), int(env["KERNEL2_TO"])
        if hi - lo > MIN_SLICE:
            retries.append((side, lo, hi))
            mid = (lo + hi) // 2
            return [r for half in ((lo, mid), (mid, hi)) for r in run_phase(
                path, side, {**env, "KERNEL2_FROM": str(half[0]), "KERNEL2_TO": str(half[1])}, retries)]
    return [(env, code, text)]


def side_rows(side, rows, retries):
    path = program(side)
    out, counts, ok = {}, collections.Counter(), True
    phases = [{"KERNEL2_PHASE": "oracle", "KERNEL2_FROM": str(i), "KERNEL2_TO": str(min(rows, i + SLICE))}
              for i in range(0, rows, SLICE)] + [{"KERNEL2_PHASE": "native"}]
    for phase in phases:
        for env, code, text in run_phase(path, side, phase, retries):
            if code != 0 or "KERNEL2_SLICE_PASS" not in text:
                ok = False
                print("FAILED", side, env, text[-3000:])
            for line in text.splitlines():
                if line.startswith("R "):
                    _, index, agrees, outcome = line.split(" ", 3)
                    out[("R", int(index))] = (agrees == "1", OBJ.sub("#<obj>", outcome))
                elif line.startswith("X "):
                    _, index, name, outcome = line.split(" ", 3)
                    out[("X", int(index))] = (name, OBJ.sub("#<obj>", outcome))
                elif line.startswith("C "):
                    _, label, n = line.split(" ")
                    counts[label] += int(n)
                elif line.startswith("(FAIL"):
                    print(side, line[:600])
    return out, counts, ok


def main():
    cases = [line for line in (OUT / "oracle-cases.sexp").read_text().splitlines() if line]
    keys = [re.match(r'\("([^"]*)"', line).group(1) for line in cases]
    retries = []
    base, _, base_ok = side_rows("base", len(cases), retries)
    new, counts, new_ok = side_rows("new", len(cases), retries)
    print("gsi slices re-run as halves after a GC crash:", len(retries))
    tally = collections.Counter()
    by_fn = collections.defaultdict(collections.Counter)
    failures = []
    for k, (agrees, outcome) in sorted((k, v) for k, v in new.items() if k[0] == "R"):
        name = keys[k[1]]
        b = base.get(k)
        if agrees:
            tally["rt new=beam"] += 1
            by_fn[name]["=beam"] += 1
            if b and not b[0]:
                tally["rt new=beam where base/=beam (rewrite fixed)"] += 1
        elif b and b[1] == outcome:
            tally["rt new/=beam, new=base (pre-existing leaf difference)"] += 1
            by_fn[name]["=base/=beam"] += 1
        else:
            tally["rt FAIL"] += 1
            failures.append((name, cases[k[1]][:200], outcome[:200], b and b[1][:200]))
    for k, (name, outcome) in new.items():
        if k[0] != "X":
            continue
        b = base.get(k)
        if b and b == (name, outcome):
            tally["exotic new=base"] += 1
        else:
            tally["exotic FAIL"] += 1
            failures.append(("exotic " + name, str(k), outcome[:200], b and b[1][:200]))
    print("rows", len(cases))
    for label in sorted(counts):
        print(label, counts[label])
    for label in sorted(tally):
        print(label, tally[label])
    for name in sorted(by_fn):
        print("  ", name, dict(by_fn[name]))
    for f in failures[:60]:
        print("FAIL", f)
    ok = base_ok and new_ok and not failures and tally["rt new=beam"] > 0
    print("KERNEL2_CHECK_PASS" if ok else "KERNEL2_CHECK_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
