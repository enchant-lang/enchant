#!/usr/bin/env python3
"""DATA differential, native half: run the BEAM oracle rows against the
compiled host modules in gsi.

Program = this checkout's host sources (prepare-host.py order, after the
          cutover) + the new category-(b) host files of this workstream
        + the compiled closure definitions the modules reach, extracted from
          the reference prelude (read-only) by extract.py
        + out/a/data.scm (emit.bl) + out/targets.scm (generated here)
        + check.scm
Run under `work run`:  python3 research/native-seed/speed/data/check.py [--slice N]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NS = HERE.parents[1]
MAIN = Path("/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/native-speed/"
            "research/native-seed/out/speed-build")
HOST = [NS / p for p in ("host.scm", "host/host-values.scm", "host/host-leaves.scm", "host/host-lazy.scm",
                          "host/host-extra.scm", "host/host-compiler.scm", "host/host-match.scm",
                          "host/host-kernel.scm", "host/native-gb-trees.scm", "host/native-data-bifs.scm")]
MODULES = {"Elixir.BeamLisp.Num": "host.num", "Elixir.BeamLisp.Decimal": "host.decimal",
           "Elixir.BeamLisp.ExInfo": "host.ex-info", "Elixir.BeamLisp.CompileError": "host.compile-error",
           "Elixir.BeamLisp.Sorted": "host.sorted", "Elixir.BeamLisp.Transient": "host.transient"}


def ident(s):
    return "v" + "".join("_" + str(ord(c)) for c in s)


def text(s):
    return json.dumps(s)


def targets(cases, emitted):
    keys = sorted({re.match(r'\("([^"]+)"', line).group(1) for line in cases.read_text().splitlines() if line})
    defined = set(re.findall(r"^\(define (v_[0-9_]+\$\d+) #f\)$", emitted.read_text(), re.M))
    rows = []
    for key in keys:
        module, fun, arity = key.rsplit("/", 2)[0], key.rsplit("/", 2)[1], key.rsplit("/", 1)[1]
        ns = MODULES.get(module)
        cell = ident(ns + "/" + fun) + "$" + arity if ns else None
        compiled = cell if cell in defined else "#f"
        rows.append(f"(list {text(key)} {compiled} (let ((l (native-leaf {text(key)}))) (if (eq? l native-missing) #f l)))")
    return "(define data-targets (list\n" + "\n".join(rows) + "))\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--emitted", default=str(HERE / "out/a/data.scm"))
    parser.add_argument("--cases", default=str(HERE / "out/oracle-cases.sexp"))
    parser.add_argument("--extra", action="append", default=[], help="more Scheme files to load before check.scm")
    parser.add_argument("--from", dest="start", default="0")
    parser.add_argument("--to", default="1000000000")
    parser.add_argument("--program-only", action="store_true")
    args = parser.parse_args()
    out = HERE / "out"
    emitted, cases = Path(args.emitted), Path(args.cases)
    (out / "targets.scm").write_text(targets(cases, emitted))
    subset = out / "closure-subset.scm"
    extract = subprocess.run([sys.executable, str(HERE / "extract.py"), str(MAIN / "prelude.scm"), str(emitted), str(subset)],
                             text=True, stdout=subprocess.PIPE, check=True)
    print(extract.stdout.splitlines()[0], flush=True)
    parts = [*HOST, subset, emitted, out / "targets.scm",
             *[Path(p) for p in args.extra], HERE / "check.scm"]
    program = out / "check-run.scm"
    program.write_text("\n".join(p.read_text() for p in parts) + "\n")
    if args.program_only:
        print(program)
        return 0
    gambit = Path(json.loads((NS / "toolchain-pin.json").read_text())["gambit"])
    env = {**os.environ, "DATA_CASES": str(cases), "DATA_FROM": args.start, "DATA_TO": args.to}
    result = subprocess.run(["timeout", "-s", "KILL", "1500", str(gambit / "bin/gsi"), str(program)],
                            cwd=out, env=env, stdin=subprocess.DEVNULL)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
