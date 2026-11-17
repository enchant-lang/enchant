#!/usr/bin/env python3
"""FRAMES: assemble and run the gsi programs for frames.check, then compare.

Usage: run.py OUT   (OUT holds old-*.scm and new-*.scm from check.bl, probes.scm,
and old-host/ = the pre-N4 host files from git HEAD~ of this branch.)
Programs: {old,new} x {release,frames}. Debug programs append the source-frame
host. Old-vs-new must print the same VALUE/SHOW/TRACE lines; TURNS and TICKS are
the budget counts N4 is allowed to change.
"""
import json, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
GSI = Path(json.loads((BASE / "toolchain-pin.json").read_text())["gambit"]) / "bin/gsi"
HOST = ["host.scm", "host/host-values.scm", "host/host-leaves.scm", "host/host-extra.scm",
        "host/native-memo.scm", "host/host-compiler.scm", "host/host-match.scm"]
RESET_NEW = "(set! frames-reset! (lambda () (set! native-source-frames '()) (set! native-source-pending #f)))"

def program(variant, mode):
    root = OUT / "old-host" if variant == "old" else BASE
    parts = [(root / p).read_text() for p in HOST]
    if mode == "frames":
        parts.append((root / "host/host-source-frames.scm").read_text())
    parts.append((BASE / "speed/frames/harness.scm").read_text())
    if mode == "frames" and variant == "new":
        parts.append(RESET_NEW)
    parts.append((OUT / f"{variant}-{mode}.scm").read_text())
    parts.append((OUT / "probes.scm").read_text())
    path = OUT / f"program-{variant}-{mode}.scm"
    path.write_text("\n".join(parts) + "\n")
    return path

results = {}
for variant in ("old", "new"):
    for mode in ("release", "frames"):
        path = program(variant, mode)
        run = subprocess.run(["timeout", "120", str(GSI), str(path)], cwd=OUT, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (OUT / f"{variant}-{mode}.log").write_text(run.stdout)
        lines = run.stdout.splitlines()
        results[(variant, mode)] = lines
        print(f"{variant}-{mode}: exit {run.returncode}; " + (lines[-1] if lines else "<no output>"))

def observed(lines):
    return [l for l in lines if l.split(" ", 1)[0] in ("VALUE", "VALUE_INFO", "SHOW", "TRACE", "FRAMES_FAIL")]

status = 0
for mode in ("release", "frames"):
    old, new = observed(results[("old", mode)]), observed(results[("new", mode)])
    same = old == new
    print(f"{mode}: {len(new)} observation lines; old == new: {same}")
    if not same:
        status = 1
        for a, b in zip(old, new):
            if a != b:
                print("  old:", a[:400]); print("  new:", b[:400])
        if len(old) != len(new):
            print("  length", len(old), len(new))
    counts = {}
    for variant in ("old", "new"):
        for l in results[(variant, mode)]:
            if l.startswith(("TURNS ", "TICKS ")):
                key = l.rsplit(" turns=", 1)[0] if l.startswith("TURNS ") else l.rsplit(" ", 1)[0]
                counts.setdefault(key, {})[variant] = l.rsplit(" ", 2)[-2:] if l.startswith("TURNS ") else l.rsplit(" ", 1)[-1]
    for key, row in counts.items():
        print(f"  {mode} {key}: old={row.get('old')} new={row.get('new')}")
for key, lines in results.items():
    if not lines or not lines[-1].startswith("FRAMES_CHECKS") or not lines[-1].endswith("FAILURES 0"):
        status = 1
sys.exit(status)
