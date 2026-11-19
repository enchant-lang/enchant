#!/usr/bin/env python3
"""Compare and resume eager, on-demand and ordinary linking on retained inputs."""

import argparse
import filecmp
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

SEED = Path("research/native-seed")
FRONT = SEED / "speed/front"
ROOT = Path(__file__).resolve().parents[4]
SOURCES = ("priv", *(str(SEED / path) for path in
                   ("run", "sdk-pin.json", "partition-closure.py", "src", "speed")))
MODES = {"eager", "on-demand", "ordinary"}


def read(path):
    return json.loads(path.read_bytes())


def save(path, data):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def partition_paths(manifest):
    document = read(manifest)
    return [manifest, *(manifest.parent / row["path"] for row in
            [document["metadata"], *document["units"]]),
            manifest.parent / document["artifact_path"]]


def seal(paths, base=None):
    return {str(path.relative_to(base) if base else path): digest(path)
            for path in sorted(paths)}


def source_paths(root):
    for name in SOURCES:
        path = root / name
        yield from (file for file in path.rglob("*") if file.is_file()) if path.is_dir() else (path,)


def new_overlay(work, revision, prefix):
    overlay = Path(tempfile.mkdtemp(prefix=prefix, dir=work))
    with tempfile.TemporaryFile() as archive:
        subprocess.run(["git", "archive", revision, "--", *SOURCES],
                       stdout=archive, cwd=ROOT, check=True)
        archive.seek(0)
        subprocess.run(["tar", "-xf", "-", "-C", overlay], stdin=archive, check=True)
    runtime = overlay / "runtime"
    runtime.mkdir(mode=0o700)
    seed_runtime = overlay / SEED / ".runtime"
    seed_runtime.mkdir()
    (seed_runtime / "path").write_text(str(runtime) + "\n")
    return overlay


def capture(work, request):
    baseline, qualification, samples = map(Path, request["arguments"])
    marker = work / "capture.json"
    request_digest = digest(work / "plan.json")
    if marker.exists():
        state = read(marker)
        if state["request"] != request_digest:
            raise ValueError("Capture belongs to a different request")
        overlay = Path(state["overlay"])
        verify_source(state["source"], overlay)
    else:
        overlay = new_overlay(work, request["revision"], "capture-")
        state = {"overlay": str(overlay), "request": request_digest,
                 "source": seal(source_paths(overlay), overlay), "finished": {}}
        save(marker, state)
    base = [overlay / SEED / "run", "run", FRONT / "observe-links.bl", "--",
            str(baseline / "partition.json"), str(baseline / "link-rows.etf")]
    for filename, mode, args in (
            ("stage-plan.etf", "--capture-stage-link-plan", [qualification, overlay / "stage-checkpoints"]),
            ("bound-donor.etf", "--capture-bound-registry", [samples, qualification])):
        output = overlay / filename
        saved = state["finished"].get(filename)
        if saved:
            verify({filename: saved["sha256"]}, overlay)
            continue
        started = time.monotonic()
        subprocess.run([*base, mode, output, *args], cwd=overlay, check=True)
        elapsed = time.monotonic() - started
        verify_source(state["source"], overlay)
        state["finished"][filename] = {"sha256": digest(output), "wall-seconds": elapsed}
        save(marker, state)
    verify_source(state["source"], overlay)
    return overlay, sum(row["wall-seconds"] for row in state["finished"].values())


def prepare(work, request):
    baseline, qualification, samples = map(Path, request["arguments"])
    captured, capture_seconds = capture(work, request)
    overlay = new_overlay(work, request["revision"], "overlay-")
    plan = overlay / "stage-plan.etf"
    receipt = overlay / "bound-donor.etf"
    for path in (plan, receipt):
        shutil.copyfile(captured / path.name, path)
    subprocess.run(["python3", FRONT / "edit-relink-fixture.py", SEED / "src/native/scheme.bl",
                    request["edit"]], cwd=overlay, check=True)
    source = seal(source_paths(overlay), overlay)
    staged = overlay / "prepared"
    staged.mkdir()
    for name in ("partition.json", "link-rows.etf"):
        shutil.copyfile(baseline / name, staged / name)
    run_update(overlay, staged, "--prepare", {})
    verify_source(source, overlay)
    save(overlay / "linked-request.json",
         {"donor": str(baseline / "partition.json"), "qualification": str(qualification),
          "samples": str(samples), "receipt": str(receipt), "sha256": digest(receipt),
          "plan": str(plan), "stage-plan-sha256": digest(plan)})
    return {"overlay": str(overlay), "capture-wall-seconds": capture_seconds,
            "source": source,
            "inputs": seal([plan, receipt, overlay / "linked-request.json",
                            staged / "link-rows.etf", *partition_paths(staged / "partition.json")], overlay)}


def run_update(overlay, directory, step, environment):
    command = ["systemd-run", "--user", "--quiet", "--collect", "--wait", "--pipe",
               f"--working-directory={overlay}", "--property=MemoryMax=3G",
               "--property=MemorySwapMax=0", "--property=RuntimeMaxSec=420",
               "--property=KillMode=control-group", f"--setenv=XDG_RUNTIME_DIR={overlay / 'runtime'}",
               "/usr/bin/env", "-u", "NATIVE_CHECKED_RELINK_REQUEST", "-u", "NATIVE_STAGE_LINK_PLAN_REQUEST",
               "-u", "NATIVE_RELINK_LAZY_MACROS", "-u", "NATIVE_RELINK_PROFILE",
               "NATIVE_RELINK_TIMINGS=1", *(f"{key}={value}" for key, value in environment.items()),
               overlay / SEED / "speed/final/closure-r3.sh", directory, step]
    subprocess.run(command, cwd=overlay, check=True)


def run_link(overlay, work, mode, profile, staged=None):
    staged = staged if staged is not None else overlay / "prepared"
    destination = Path(tempfile.mkdtemp(prefix=mode + "-", dir=work))
    manifest = read(staged / "partition.json")
    for row in [manifest["metadata"], *manifest["units"]]:
        relative = Path(row["path"]).relative_to(staged)
        local = destination / relative
        local.parent.mkdir(exist_ok=True)
        shutil.copyfile(staged / relative, local)
        row["path"] = str(relative)
    manifest["artifact_path"] = "closure.etf"
    save(destination / "partition.json", manifest)
    for name in ("closure.etf", "link-rows.etf"):
        shutil.copyfile(staged / name, destination / name)
    environment = {"NATIVE_RELINK_PROFILE": "1" if profile else "0"}
    if mode != "ordinary":
        environment["NATIVE_STAGE_LINK_PLAN_REQUEST"] = str(overlay / "linked-request.json")
        environment["NATIVE_RELINK_LAZY_MACROS"] = "1" if mode == "on-demand" else "0"
    run_update(overlay, destination, "--link", environment)
    update = read(destination / "update.json")
    if mode == "ordinary":
        if "stage-link-candidate" in update:
            raise ValueError("Ordinary updater selected the guarded path")
    elif update["stage-link-candidate"]["macro-constructors"]["mode"] != mode:
        raise ValueError(f"Expected {mode} constructor binding")
    paths = [*partition_paths(destination / "partition.json"), destination / "link-rows.etf",
             destination / "update.json", destination / "linked-pass.seconds",
             destination / "final-partition.seconds"]
    result = seal(paths, destination)
    if result["closure.etf"] != update["artifact-sha256"]:
        raise ValueError("The updater report names a different closure")
    return {"mode": mode, "directory": str(destination), "files": result}


def verify(mapping, base):
    if seal([base / path for path in mapping], base) != mapping:
        raise ValueError(f"Retained inputs or results changed under {base}")


def verify_source(mapping, overlay):
    verify(mapping, overlay)
    if set(source_paths(overlay)) != {overlay / path for path in mapping}:
        raise ValueError("Retained Source inventory differs from the prepared request")


def verify_donor(inputs, request):
    if seal(inputs) != request["inputs"]:
        raise ValueError("Donor inputs changed during the comparison")


def verify_prepared(prepared, overlay):
    verify_source(prepared["source"], overlay)
    verify(prepared["inputs"], overlay)


def timings(path):
    wall, user, system = map(float, path.read_text().split())
    return {"wall": wall, "user": user, "system": system, "cpu": round(user + system, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("qualification", type=Path)
    parser.add_argument("samples", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--order", default="eager,on-demand,ordinary")
    parser.add_argument("--arity", action="store_true")
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--stop-after", type=int, help="Return after this many completed passes")
    args = parser.parse_args()
    order = args.order.split(",")
    if set(order) != MODES:
        parser.error("--order must include eager,on-demand,ordinary")
    if args.stop_after is not None and not 1 <= args.stop_after <= len(order):
        parser.error("--stop-after must select a pass in --order")
    work = args.work.resolve()
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    baseline, qualification, samples = (p.resolve(strict=True) for p in
                                        (args.baseline, args.qualification, args.samples))
    inputs = [*partition_paths(baseline / "partition.json"), baseline / "link-rows.etf",
              qualification, samples]
    with (work / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = work / "plan.json"
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        request = {"version": 1, "revision": read(plan)["revision"] if plan.exists() else head,
                   "arguments": list(map(str, (baseline, qualification, samples))),
                   "inputs": seal(inputs), "order": order, "profile": args.profile,
                   "edit": "--arity" if args.arity else ""}
        if plan.exists():
            if read(plan) != request:
                raise ValueError("Arguments or donor inputs differ from the retained request")
        else:
            save(plan, request)
        preparation = work / "preparation.json"
        if not preparation.exists():
            prepared = prepare(work, request)
            verify_donor(inputs, request)
            save(preparation, prepared)
        prepared = read(preparation)
        overlay = Path(prepared["overlay"])
        verify_prepared(prepared, overlay)
        passes = []
        for i, mode in enumerate(order[:args.stop_after], 1):
            marker = work / f"pass-{i}.json"
            if marker.exists():
                row = read(marker)
                if row["mode"] != mode or row["preparation"] != digest(preparation):
                    raise ValueError("Pass receipt belongs to a different request")
                verify(row["files"], Path(row["directory"]))
                print(f"Reused {mode} pass {i}", flush=True)
            else:
                row = run_link(overlay, work, mode, args.profile)
                verify_prepared(prepared, overlay)
                verify_donor(inputs, request)
                row["preparation"] = digest(preparation)
                save(marker, row)
            passes.append(row)
        verify_prepared(prepared, overlay)
        verify_donor(inputs, request)
        if len(passes) < len(order):
            return
        for name in ("closure.etf", "link-rows.etf"):
            first = Path(passes[0]["directory"]) / name
            if not all(filecmp.cmp(first, Path(row["directory"]) / name, shallow=False)
                       for row in passes[1:]):
                raise ValueError(f"Linked artifacts disagree on {name}")
        for row in passes:
            row["linked-pass-seconds"] = timings(Path(row["directory"]) / "linked-pass.seconds")
        report = {"request": request, "capture-wall-seconds": prepared["capture-wall-seconds"],
                  "preparation-sha256": digest(preparation), "passes": passes,
                  "preparation-seconds": {phase: timings(overlay / "prepared" / f"{phase}.seconds")
                                          for phase in ("source-pass", "member-rows", "first-partition")},
                  "exact-closure": True, "exact-link-rows": True}
        save(work / "comparison.json", report)


if __name__ == "__main__":
    main()
