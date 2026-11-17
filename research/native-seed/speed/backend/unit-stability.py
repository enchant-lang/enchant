#!/usr/bin/env python3
"""U check: content-addressed stage-1 units.

Copies a real stage1.scm into SCRATCH, splits it with the driver's own
split_source (fixpoint-full.py) and keys every unit with the driver's own
unit_cache_request. Then:
  1. an unchanged re-split must reuse every key;
  2. each body edit (grow or shrink one definition) must change exactly the
     unit(s) holding the edited definition, and reuse every other key.
With --baseline the same edits are replayed through the previous greedy
splitter (git HEAD~ version given as a path) for comparison.

usage: unit-stability.py STAGE1_DIR SCRATCH [--edits N] [--baseline OLD_SPLITTER]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import random
import shutil
import subprocess
import time

here = Path(__file__).resolve()
base = here.parents[2]
spec = importlib.util.spec_from_file_location("fixpoint_full", base / "fixpoint-full.py")
fx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)

parser = argparse.ArgumentParser()
parser.add_argument("stage1_dir", type=Path)
parser.add_argument("scratch", type=Path)
parser.add_argument("--edits", type=int, default=6)
parser.add_argument("--baseline", type=Path)
parser.add_argument("--seed", type=int, default=7)
args = parser.parse_args()

tools = json.loads((base / "toolchain-pin.json").read_text())
gsi = Path(tools["gambit"]) / "bin/gsi"
scratch = args.scratch.resolve()
shutil.rmtree(scratch, ignore_errors=True)
scratch.mkdir(parents=True)
host = scratch / "host.scm"
shutil.copyfile(args.stage1_dir / "host.scm", host)
original = (args.stage1_dir / "stage1.scm").read_bytes()
host_unit = fx.HEADER + host.read_bytes() + b"\n"
assert original.startswith(host_unit)
TOOLS = {"fixture": "unit-stability"}  # the real driver binds gsc/clang/flags here


def run(label, argv, cwd=None):
    started = time.monotonic()
    done = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, timeout=600)
    if done.returncode:
        raise RuntimeError(label + ": " + done.stdout[-2000:] + done.stderr[-2000:])
    run.seconds = time.monotonic() - started
    return done.stdout


def split(name, body, splitter):
    out = scratch / name
    out.mkdir()
    source = out / "stage1.scm"
    source.write_bytes(body)
    folder, manifest = fx.split_source(source, host_unit=host_unit, host_scheme=host, gsi=gsi,
                                       splitter=splitter, out=out, run=run)
    keys = [fx.key(fx.unit_cache_request(row, i, TOOLS)) for i, row in enumerate(manifest["units"])]
    texts = [(folder / row["file"]).read_text() for row in manifest["units"]]
    return {"keys": keys, "texts": texts, "rows": manifest["units"], "seconds": run.seconds, "folder": folder}


lines = original.decode().split("\n")
host_lines = host_unit.decode().count("\n")
candidates = [i for i, line in enumerate(lines) if i > host_lines and line.startswith("(define v_")
              and "$" not in line.split(" ", 2)[1] and len(line) > 400 and line.endswith(")")]
rng = random.Random(args.seed)
picked = sorted(rng.sample(candidates, args.edits))


def edited(index, grow):
    line = lines[index]
    name = line.split(" ", 2)[1]
    prefix = "(define " + name + " "
    body = line[len(prefix):-1]
    if grow:  # +~3 KB, still a valid definition
        new = prefix + "(begin (quote (" + " ".join(["pad"] * 750) + ")) " + body + "))"
    else:     # -~ the body: a smaller valid definition
        new = prefix + "(lambda args bl-nil))"
    copy = list(lines)
    copy[index] = new
    return name, "\n".join(copy).encode()


def holders(result, name):
    marker = "(define " + name + " "
    return [i for i, text in enumerate(result["texts"]) if marker in text]


def experiment(splitter, label):
    first = split(label + "-a", original, splitter)
    again = split(label + "-b", original, splitter)
    sizes = [row["bytes"] for row in first["rows"][1:]]
    report = {"splitter": str(splitter), "units": len(first["keys"]),
              "form_unit_bytes": {"min": min(sizes), "max": max(sizes), "mean": sum(sizes) // len(sizes)},
              "split_seconds": round(first["seconds"], 1),
              "unchanged_resplit_reused": sum(a == b for a, b in zip(first["keys"], again["keys"])),
              "unchanged_resplit_same_count": len(first["keys"]) == len(again["keys"]),
              "edits": []}
    print(label, "UNITS", report["units"], "bytes", report["form_unit_bytes"], "split", report["split_seconds"], "s",
          "UNCHANGED reused", report["unchanged_resplit_reused"], "/", len(first["keys"]), flush=True)
    for n, index in enumerate(picked):
        grow = n % 2 == 0
        name, body = edited(index, grow)
        shutil.rmtree(scratch / (label + "-e"), ignore_errors=True)
        after = split(label + "-e", body, splitter)
        before_keys, after_keys = set(first["keys"]), set(after["keys"])
        changed = [i for i, k in enumerate(after["keys"]) if k not in before_keys]
        holding = holders(after, name)
        exact = changed == holding
        row = {"definition": name[:60], "edit": "grow" if grow else "shrink",
               "units_after": len(after["keys"]), "changed_units": changed, "edited_definition_in": holding,
               "reused": len(after["keys"]) - len(changed), "exactly_the_edited_units": exact}
        report["edits"].append(row)
        print(label, "EDIT", row["edit"], "changed", changed, "holder", holding, "reused", row["reused"], "/",
              len(after["keys"]), "EXACT" if exact else "SPREAD", flush=True)
    return report, first


new_report, first = experiment(base / "split-top-level.scm", "new")
report = {"new": new_report}
if args.baseline:
    report["baseline"], _ = experiment(args.baseline.resolve(), "old")
(scratch / "report.json").write_text(json.dumps(report, indent=2) + "\n")
# Keep one unit for a gsc validity check by the caller.
smallest = min(range(1, len(first["rows"])), key=lambda i: first["rows"][i]["bytes"])
print("UNIT_FOR_GSC", first["folder"] / first["rows"][smallest]["file"], first["rows"][smallest]["bytes"])
print("UNIT_STABILITY_DONE", all(e["exactly_the_edited_units"] for e in new_report["edits"])
      and new_report["unchanged_resplit_reused"] == new_report["units"])
