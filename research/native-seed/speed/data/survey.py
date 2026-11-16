#!/usr/bin/env python3
"""List each DATA module's remote calls that have no registered native leaf
and no compiled target (closure namespace or another DATA module)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LEAVES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed/"
    "research/native-seed/out/speed-build/leaves.json")
MODS = ("vector vector_enumerable set set_enumerable sorted sorted_map sorted_set transient refs "
        "refs_structs num decimal ex_info multi compile_error reactive").split()
OWN = {"Elixir.BeamLisp.Vector", "Elixir.Enumerable.BeamLisp.Vector", "Elixir.BeamLisp.Set",
       "Elixir.Enumerable.BeamLisp.Set", "Elixir.BeamLisp.Sorted", "Elixir.BeamLisp.Transient",
       "Elixir.BeamLisp.Refs", "Elixir.BeamLisp.Num", "Elixir.BeamLisp.Decimal", "Elixir.BeamLisp.ExInfo",
       "Elixir.BeamLisp.Multi", "Elixir.BeamLisp.CompileError", "Elixir.BeamLisp.Reactive"}
ERL = {"erlang", "maps", "lists", "binary", "string", "unicode", "ets", "gb_trees", "math", "io_lib"}


def main():
    leaves = set(json.loads(LEAVES.read_text())["registered_leaves"])
    prefixes = {k.rsplit("/", 1)[0] for k in leaves}
    for m in MODS:
        src = "\n".join(l for l in (ROOT / f"priv/host/{m}.bl").read_text().split("\n")
                        if not l.strip().startswith(";"))
        calls = set(re.findall(r"\(([A-Za-z][A-Za-z0-9_.]*)/([^ ()\n\]]+)", src))
        miss, own = [], []
        for mo, f in sorted(calls):
            mm = mo if (mo in ERL or mo.startswith("Elixir.")) else "Elixir." + mo
            if mm in OWN:
                own.append(mm + "/" + f)
            elif mm + "/" + f not in prefixes:
                miss.append(mm + "/" + f)
        print(f"{m}\n  no-leaf: {' '.join(miss)}\n  data-module: {' '.join(own)}")


if __name__ == "__main__":
    main()
