#!/usr/bin/env python3
"""Run gsi over the native host sources (+ host-kernel.scm) followed by FILES.

Usage: gsi-run.py [--no-kernel] FILE.scm ...
Concatenates host sources exactly as check-host.py does (plus host-compiler and
host/host-kernel.scm) into speed/kernel/out/run.scm and runs the pinned gsi.
"""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
HOST = ["host.scm", "host/host-values.scm", "host/host-leaves.scm", "host/host-lazy.scm",
        "host/host-extra.scm", "host/host-compiler.scm"]


def main(argv):
    kernel = True
    if argv and argv[0] == "--no-kernel":
        kernel, argv = False, argv[1:]
    sources = [BASE / p for p in HOST] + ([BASE / "host/host-kernel.scm"] if kernel else [])
    sources += [Path(a).resolve() for a in argv]
    OUT.mkdir(parents=True, exist_ok=True)
    program = OUT / "run.scm"
    program.write_text("\n".join(p.read_text() for p in sources) + "\n")
    gambit = Path(json.loads((BASE / "toolchain-pin.json").read_text())["gambit"])
    result = subprocess.run(["timeout", "120", str(gambit / "bin/gsi"), str(program)], cwd=OUT, stdin=subprocess.DEVNULL)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
