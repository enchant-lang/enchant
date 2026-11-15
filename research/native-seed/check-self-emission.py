#!/usr/bin/env python3
"""Check one real native self-emission without rebuilding or replaying actors.

The already admitted stage1 ELF reads its original owned Source bundle and
emits a fresh Scheme candidate under the unchanged 240-second deadline. This
checker parses JSON receipts only. It launches no SDK, GSI, host toolchain compiler or Source /
ANF interpreter, and makes no stage2-execution or complete-fixpoint claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

DEADLINE = 240
HEADER = b";; BL native compiler. Generated from canonical BL source.\n"
ENTRY = b"(native-main (native-command-line))\n"
MARKER = "NATIVE_SELF_COMPILE 18 namespaces"
HOST_SOURCES = ("host.scm", "host/host-values.scm", "host/host-leaves.scm",
                "host/host-lazy.scm", "host/host-extra.scm", "host/host-compiler.scm")


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def process_snapshot(pid):
    try:
        # The command field may contain spaces or closing parentheses.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[19], int(fields[1])  # start time (field22), parent PID (field4).
    except (OSError, IndexError, ValueError):
        return None


def process_identity(pid):
    snapshot = process_snapshot(pid)
    return snapshot[0] if snapshot else None


class OwnedTree:
    """Track only the launched process and its observed descendants."""

    def __init__(self, process):
        self.process = process
        snapshot = process_snapshot(process.pid)
        self.members = {process.pid: snapshot[0]} if snapshot and snapshot[1] == os.getpid() else {}
        self.discover()

    def discover(self):
        pending, visited = [(pid, None) for pid in self.members], set()
        while pending:
            pid, expected_parent = pending.pop()
            if pid in visited:
                continue
            visited.add(pid)
            snapshot = process_snapshot(pid)
            if (snapshot is None or (pid in self.members and self.members[pid] != snapshot[0])
                    or (pid not in self.members and snapshot[1] != expected_parent)):
                continue
            self.members[pid] = snapshot[0]
            try:
                for task in Path(f"/proc/{pid}/task").iterdir():
                    try:
                        pending.extend((int(x), pid) for x in (task / "children").read_text().split())
                    except OSError:
                        pass
            except OSError:
                pass

    def cleanup(self):
        errors = []
        for _ in range(2):
            self.discover()
            for pid, identity in list(self.members.items())[::-1]:
                if process_identity(pid) != identity:
                    continue
                try:
                    # Each separately created child group is owned too. A
                    # descendant in another existing group gets only SIGKILL.
                    if os.getpgid(pid) == pid:
                        os.killpg(pid, signal.SIGKILL)
                    else:
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as error:
                    errors.append(str(error))
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            errors.append("owned native process did not reap after SIGKILL")
        return {"tracked_processes": len(self.members), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("research/native-seed/out/compiler-closure"))
    parser.add_argument("--evidence", type=Path, default=Path("research/native-seed/evidence/self-emission.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    out = (root / args.out).resolve()
    evidence = (root / args.evidence).resolve()
    base = root / "research/native-seed"
    here = Path(__file__).resolve()
    candidate = out / "stage2-candidate.scm"
    inputs, tree, process, attempt, lock = {}, None, None, None, None
    child_started, child_finished, accepted_candidate_sha256 = None, None, None
    started = time.monotonic()
    report = {"schema": "bl.native.self-emission-check", "version": 1,
              "status": "running", "scope": "admitted native stage1 ELF compiles its original Source bundle to a fresh Scheme candidate",
              "deadline_seconds": DEADLINE, "timeout": False, "sdk_launched": False,
              "checker_interprets_source_or_anf": False, "candidate_built_or_executed": False,
              "actor_corpus_replayed": False, "fixpoint_qualified": False,
              "self_emission_succeeded": False, "inputs": inputs}

    def path_for(name):
        path = Path(name)
        return path.resolve() if path.is_absolute() else (root / path).resolve()

    def bind(path, expected=None):
        path = path.resolve()
        actual = digest(path)
        require(expected is None or expected == actual, "input identity differs: " + str(path))
        require(str(path) not in inputs or inputs[str(path)] == actual, "input changed during admission: " + str(path))
        inputs[str(path)] = actual
        return actual

    def unchanged():
        for name, expected in inputs.items():
            require(Path(name).is_file() and digest(Path(name)) == expected, "input changed during native self-emission: " + name)

    def terminated(signum, frame):
        raise InterruptedError("self-emission checker received signal " + str(signum))

    previous_term = signal.signal(signal.SIGTERM, terminated)
    result = 1
    try:
        require(out.is_dir(), "native compiler artifact directory is absent")
        lock = (out / "self-emission.lock").open("a")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        build_path = out / "native-build.json"
        bind(build_path)
        build = json.loads(build_path.read_text())
        require(build.get("schema") == "bl.native.bounded-build" and build.get("version") == 1,
                "native build receipt has an unsupported schema")
        require(build.get("status") in ("stage1-compiled-not-qualified", "stage1-actors-compiled-not-qualified", "failed"),
                "native build receipt is unfinished or not a stage1 checkpoint")
        require(build.get("compile_deadline_seconds") == 120, "native build changed the compiler child deadline")
        stages = [row for row in build.get("builds", []) if row.get("stage") == "stage1"]
        require(len(stages) == 1, "native receipt must contain exactly one stage1 compiler")
        stage = stages[0]
        image = out / "stage1"
        require(path_for(stage["executable"]) == image, "native receipt selects another executable")
        for name, expected in build["inputs"].items():
            bind(path_for(name), expected)
        admitted_paths = {str(path_for(name)) for name in build["inputs"]}
        for required in (base / "fixpoint.py", base / "split-top-level.scm", base / "sdk-pin.json",
                         base / "toolchain-pin.json", out / "stage1.scm", out / "prelude.scm",
                         out / "bundle.scm", out / "host.scm", out / "identity.json", out / "chunk-export.json"):
            require(str(required) in admitted_paths, "native receipt omitted an essential stage1 input: " + str(required))
        bind(image, stage["executable_sha256"])
        with image.open("rb") as stream:
            require(stream.read(4) == b"\x7fELF" and os.access(image, os.X_OK), "stage1 is not an executable ELF")
        bind(out / "stage1.scm", stage["source_sha256"])
        bind(base / "fixpoint.py", build["driver_sha256"])
        for path in (here, base / "sdk-pin.json", base / "toolchain-pin.json",
                     out / "bundle.scm", out / "host.scm", out / "prelude.scm", out / "chunk-export.json"):
            bind(path)
        pin = json.loads((base / "sdk-pin.json").read_text())
        descriptor = Path(pin["sdk"]) / "artifact.json"
        bind(descriptor, pin["descriptor_sha256"])
        require(json.loads(descriptor.read_text())["source"] == pin["source"], "native SDK Source pin differs")
        export = json.loads((out / "chunk-export.json").read_text())
        require(export.get("schema") == "bl.native.chunk-export" and export.get("version") == 2
                and export["emission_inputs"]["sdk_descriptor_sha256"] == pin["descriptor_sha256"],
                "native assembly is not the admitted SDK-bound chunk export")
        bind(out / "prelude.scm", export["prelude_sha256"])
        bind(out / "host.scm", export["inputs"]["host_sha256"])
        frozen_host = (out / "host.scm").read_bytes()
        host_parts = [base / name for name in HOST_SOURCES]
        host_parts.append(base / "host/native-text.scm")
        for path in host_parts:
            bind(path)
        actual_host = b"\n".join(path.read_bytes() for path in host_parts[:-1]) + b"\n" + host_parts[-1].read_bytes()
        require(frozen_host == actual_host, "frozen compiler host differs from its exact current components")
        source = (out / "stage1.scm").read_bytes()
        prefix = HEADER + frozen_host + b"\n"
        require(source == (out / "prelude.scm").read_bytes() + ENTRY and source.startswith(prefix),
                "stage1 differs from its frozen host/prelude/native-main entry")
        units = stage.get("units", [])
        require(units and units[0].get("ordinal") == 0 and units[0].get("indivisible_ffi_host") is True,
                "native stage1 lacks its indivisible frozen host unit")
        bind(path_for(stage["split_manifest"]), stage["split_manifest_sha256"])
        require(stage["link_order"] == [row["c"] for row in units], "native compiler unit link order differs")
        for ordinal, row in enumerate(units):
            require(row["ordinal"] == ordinal, "native compiler unit ordinals differ")
            bind(path_for(row["c"]), row["c_sha256"])
            bind(path_for(row["object"]), row["object_sha256"])
            bind(path_for(row["c"]).with_suffix(".scm"), row["sha256"])
        report["native_build"] = {"status": build["status"], "stage": "stage1", "units": len(units),
            "host_optimization": stage["host_optimization"], "c_flags": [row["c_flags"] for row in units],
            "scheme_compiler_flags": stage["scheme_compiler_flags"],
            "later_gate_failure_does_not_disqualify_the_hash_admitted_stage1": build["status"] == "failed"}
        report["sdk_pin"] = pin
        require(not candidate.is_symlink(), "self-emission candidate must not be a symlink")
        require(not candidate.exists() or candidate.is_file(), "self-emission candidate is not a regular file")
        require(str(candidate.resolve()) not in inputs, "self-emission candidate aliases an admitted input")
        unchanged()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        attempt = out / "self-emission-attempts" / (stamp + "-" + uuid.uuid4().hex[:12])
        attempt.mkdir(parents=True, exist_ok=False)
        report["attempt_directory"] = str(attempt)
        if candidate.exists():
            previous = {"path": str(candidate), "sha256": digest(candidate), "bytes": candidate.stat().st_size}
            archive = attempt / "prior-stage2-candidate.scm"
            candidate.replace(archive)
            previous["archived_path"] = str(archive)
            require(digest(archive) == previous["sha256"], "previous candidate changed while archiving")
            report["previous_candidate"] = previous
        require(not candidate.exists(), "native candidate must be absent before invocation")
        argv = [str(image), "--compile", str(out / "bundle.scm"), str(out / "host.scm"), str(candidate)]
        env = os.environ.copy()
        env["BL_NATIVE_TRACE"] = "0"
        report["argv"] = argv
        report["environment_overrides"] = {"BL_NATIVE_TRACE": "0"}
        report["runtime_environment_sha256"] = hashlib.sha256(json.dumps(env, sort_keys=True).encode()).hexdigest()
        log = attempt / "stdout.log"
        report["log_path"] = str(log)
        child_started = time.monotonic()
        with log.open("w") as stream:
            process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            tree = OwnedTree(process)
            deadline = child_started + DEADLINE
            while process.poll() is None:
                tree.discover()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    report["timeout"] = True
                    raise subprocess.TimeoutExpired(argv, DEADLINE)
                try:
                    process.wait(timeout=min(1, remaining))
                except subprocess.TimeoutExpired:
                    pass
        child_finished = time.monotonic()
        report["child_seconds"] = round(child_finished - child_started, 3)
        if child_finished - child_started > DEADLINE:
            report["timeout"] = True
            raise subprocess.TimeoutExpired(argv, DEADLINE)
        report["exit"] = process.returncode
        unchanged()
        output = log.read_text(errors="replace")
        report["stdout"] = output
        report["log_sha256"] = digest(log)
        print(output, end="", flush=True)
        require(process.returncode == 0, "native self-emission exited " + str(process.returncode))
        require([line for line in output.splitlines() if line.startswith("NATIVE_SELF_COMPILE ")] == [MARKER],
                "native self-emission lacks its exact eighteen-namespace witness")
        require(candidate.is_file() and not candidate.is_symlink(), "native self-emission did not create its fresh candidate")
        emitted = candidate.read_bytes()
        require(emitted.startswith(prefix) and emitted.endswith(ENTRY) and len(emitted) > len(prefix) + len(ENTRY),
                "native candidate changed its frozen host prefix or native-main entry")
        accepted_candidate_sha256 = hashlib.sha256(emitted).hexdigest()
        report.update({"status": "pass", "self_emission_succeeded": True,
                       "marker": MARKER, "frozen_host_prefix_equal": True,
                       "native_main_entry_equal": True, "candidate_was_fresh": True})
        result = 0
    except BaseException as error:
        report.update({"status": "fail", "error": str(error), "error_type": type(error).__name__})
        result = 130 if isinstance(error, KeyboardInterrupt) else 1
        print("NATIVE_SELF_EMISSION_FAIL " + str(error), file=sys.stderr, flush=True)
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if tree is not None:
            report["cleanup"] = tree.cleanup()
            if report["cleanup"]["errors"]:
                report["status"], result = "fail", 1
                report["cleanup_failed"] = True
            report["exit"] = process.returncode
        if child_started is not None:
            if child_finished is None:
                child_finished = time.monotonic()
            report["child_seconds"] = round(child_finished - child_started, 3)
        if report["status"] == "pass":
            try:
                unchanged()
                require(candidate.is_file() and digest(candidate) == accepted_candidate_sha256,
                        "native candidate changed after its acceptance checks")
            except BaseException as error:
                report.update({"status": "fail", "error": str(error), "error_type": type(error).__name__})
                result = 1
        if "log_path" in report and Path(report["log_path"]).is_file():
            log = Path(report["log_path"])
            report["log_sha256"] = digest(log)
            report["stdout"] = log.read_text(errors="replace")
        if candidate.is_file() and not candidate.is_symlink():
            report["candidate"] = {"path": str(candidate), "sha256": digest(candidate), "bytes": candidate.stat().st_size,
                                   "accepted": report["status"] == "pass"}
        report["seconds"] = round(time.monotonic() - started, 3)
        if attempt is not None:
            save(attempt / "report.json", report)
        save(evidence, report)
        if lock is not None:
            lock.close()
        signal.signal(signal.SIGTERM, previous_term)
    print("NATIVE_SELF_EMISSION_" + ("PASS " if result == 0 else "FAILED ") + str(evidence), flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
