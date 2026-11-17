#!/usr/bin/env python3
"""Run a prepared native actor program in the pinned gsi (round-3 ACTOR).

Usage: run-native.py PROGRAM CLOSURE-DIR [--memo frozen|worktree] [--budget B]
                     [--timeout S] [--log PATH] [--oracle ORACLE.json]

PROGRAM is speed/actor/prepare.bl's program.scm: the closure prelude (whose
host is the frozen round-2 host.scm) followed by the actor runtime and the
application. The transport is corpus/qualify.py's GSI transport: the frozen
host's native-text FFI suffix is replaced by a `load` of the closure's
compiled text.o1; every other byte is unchanged, except with
`--memo worktree`, which replaces the frozen host's copy of
host/native-memo.scm (as committed at HEAD~ of this change, i.e. the round-2
file) by this worktree's host/native-memo.scm. That is the only way to test a
native-memo.scm change without rebuilding the image.

With --oracle (evidence/original-actor-corpus/oracle.json) the ordered PASS
labels and EXIT-PARITY/SUP-PARITY/SUP-TRACE rows are compared with round 1's
JavaScript oracle for that budget, and the witness line is checked as
qualify.py checks it. Prints one ACTOR_NATIVE line; exit 0 only on success.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys


BASE = pathlib.Path(__file__).resolve().parents[2]
ROOT = BASE.parents[1]
HEADER = b";; BL native compiler. Generated from canonical BL source.\n"
ZERO = {"procs": 0, "monitors": 0, "tables": 0, "names": 0, "table_names": 0,
        "runnable": 0, "input_sink": None, "critical": 0, "errors": 0}


def round2_memo() -> bytes:
    # The frozen round-2 host carries the native-memo.scm of the integration
    # base (the parent of this workstream's first commit).
    base = subprocess.run(["git", "-C", str(ROOT), "merge-base", "HEAD", "worktree-native-speed"],
                          check=True, capture_output=True, text=True).stdout.strip()
    return subprocess.run(["git", "-C", str(ROOT), "show", base + ":research/native-seed/host/native-memo.scm"],
                          check=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=pathlib.Path)
    parser.add_argument("closure", type=pathlib.Path)
    parser.add_argument("--memo", choices=["frozen", "worktree"], default="frozen")
    parser.add_argument("--budget", default="default")
    parser.add_argument("--timeout", type=int, default=1500)
    parser.add_argument("--log", type=pathlib.Path)
    parser.add_argument("--oracle", type=pathlib.Path)
    args = parser.parse_args()
    program = args.program.read_bytes()
    host = (args.closure / "host.scm").read_bytes()
    text = (BASE / "host/native-text.scm").read_bytes()
    suffix = b"\n" + text
    if not program.startswith(HEADER + host + b"\n") or not host.endswith(suffix):
        raise SystemExit("program does not start with the closure's frozen host")
    pure = host[:-len(suffix)]
    if args.memo == "worktree":
        old, new = round2_memo(), (BASE / "host/native-memo.scm").read_bytes()
        if pure.count(old) != 1:
            raise SystemExit("frozen host does not hold exactly one round-2 native-memo.scm")
        pure = pure.replace(old, new)
    load = ("\n(load " + json.dumps(str((args.closure / "text.o1").resolve())) + ")\n").encode()
    rest = program[len(HEADER + host + b"\n"):]
    out = args.program.with_name(args.program.stem + "-gsi-" + args.memo + ".scm")
    out.write_bytes(HEADER + pure + load + rest)
    gsi = pathlib.Path(json.loads((BASE / "toolchain-pin.json").read_text())["gambit"]) / "bin/gsi"
    env = dict(os.environ, NATIVE_ACTOR_BUDGET=args.budget)
    try:
        run = subprocess.run([str(gsi), str(out)], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=args.timeout)
        output, code, timed_out = run.stdout.decode(errors="replace"), run.returncode, False
    except subprocess.TimeoutExpired as error:
        output, code, timed_out = (error.stdout or b"").decode(errors="replace"), None, True
    log = args.log or args.program.with_name(f"{args.program.stem}-{args.memo}-{args.budget}.log")
    log.write_text(output)
    lines = output.splitlines()
    labels = [line[5:] for line in lines if line.startswith("PASS ")]
    fails = [line for line in lines if line.startswith("FAIL ")]
    report = {"program": str(args.program), "memo": args.memo, "budget": args.budget, "exit": code,
              "timed_out": timed_out, "pass": len(labels), "fail": len(fails), "log": str(log)}
    ok = code == 0 and not fails and not timed_out
    if args.oracle:
        oracle = json.loads(args.oracle.read_text())["budgets"][args.budget]
        traces = [line for line in lines if line.startswith(("EXIT-PARITY ", "SUP-PARITY ", "SUP-TRACE "))]
        witness = [json.loads(line[len("NATIVE_CORPUS_WITNESS "):]) for line in lines
                   if line.startswith("NATIVE_CORPUS_WITNESS ")]
        report.update({
            "all_pass": "js-actors: ALL PASS" in lines,
            "labels_equal_round1": labels == oracle["labels"],
            "traces_equal_round1": traces == oracle["traces"],
            "missing": [x for x in oracle["labels"] if x not in labels],
            "extra": [x for x in labels if x not in oracle["labels"]],
            "witness_budget": witness[0].get("budget") if len(witness) == 1 else None,
            "cleanup_zero": len(witness) == 1 and witness[0].get("cleanup") == ZERO,
            "witness_last": bool(lines) and lines[-1].startswith("NATIVE_CORPUS_WITNESS ")})
        ok = ok and all(report[k] for k in ("all_pass", "labels_equal_round1", "traces_equal_round1",
                                            "cleanup_zero", "witness_last"))
    report["fails"] = fails[:20]
    if not ok:
        report["tail"] = output[-2500:]
    print("ACTOR_NATIVE " + json.dumps(report), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
