#!/usr/bin/env python3
"""List the rt rows where the compiled rewritten rt.bl (`new`) differs from BEAM,
with the BEAM and native outcomes. check.py has already proved each of them
equals the compiled ORIGINAL rt.bl (`base`); this names them for RESULT.md."""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check  # noqa: E402

cases = [line for line in (check.OUT / "oracle-cases.sexp").read_text().splitlines() if line]
first = next(i for i, line in enumerate(cases) if line.startswith('("rt/'))
path = check.program("new")
for lo in range(first, len(cases), check.SLICE):
    env = {"KERNEL2_PHASE": "oracle", "KERNEL2_FROM": str(lo), "KERNEL2_TO": str(lo + check.SLICE)}
    for _, _, text in check.run_phase(path, "new", env, []):
        for line in text.splitlines():
            if line.startswith("R ") and line.split(" ", 3)[2] == "0":
                _, index, _, outcome = line.split(" ", 3)
                print(cases[int(index)][:160], "| native:", outcome[:120])
