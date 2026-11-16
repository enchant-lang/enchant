#!/usr/bin/env python3
"""Native kernel differential check (workstream K).

1. BEAM oracle (once, ~20 s):
     research/native-seed/run run research/native-seed/speed/kernel/oracle.bl -- research/native-seed/speed/kernel/out
2. This script:  python3 research/native-seed/speed/kernel/check.py
   Concatenates host sources + host/host-kernel.scm + out/oracle.scm +
   kernel-check.scm and runs the pinned gsi (timeout 120 s per process):
   BEAM rows in slices of SLICE rows (see kernel-check.scm for why), then the
   native-only sections. Prints aggregated counts; exit 0 only when all pass.
"""
import collections
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLICE = 15000


def run(env):
    result = subprocess.run([sys.executable, str(HERE / "gsi-run.py"), str(HERE / "out/oracle.scm"),
                             str(HERE / "kernel-check.scm")], env={**os.environ, **env},
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode, result.stdout


def main():
    rows = sum(1 for _ in open(HERE / "out/oracle-cases.sexp"))
    counts = collections.Counter()
    ok = True
    phases = [{"KERNEL_PHASE": "oracle", "KERNEL_FROM": str(i), "KERNEL_TO": str(i + SLICE)}
              for i in range(0, rows, SLICE)] + [{"KERNEL_PHASE": "native"}]
    for env in phases:
        code, out = run(env)
        passed = code == 0 and "KERNEL_DIFFERENTIAL_PASS" in out
        ok = ok and passed
        for label, n in re.findall(r"^(\S+) (\d+)$", out, re.M):
            counts[label] += int(n)
        for line in out.splitlines():
            if line.startswith("leaf/=beam "):
                parts = line.split()
                counts["leaf/=beam " + parts[1]] += int(parts[2])
        if not passed:
            print("FAILED", env, out[-4000:])
    print("rows", rows)
    for label in sorted(counts):
        print(label, counts[label])
    print("KERNEL_CHECK_PASS" if ok else "KERNEL_CHECK_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
