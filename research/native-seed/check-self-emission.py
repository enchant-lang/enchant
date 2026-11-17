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
                "host/host-extra.scm", "host/host-compiler.scm", "host/native-memo.scm")


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


def admit_host_parts(receipt_path, bind, path_for, base, out, stage, build_path, prefix):
    """Admit a derived image without modifying the original whole-host receipt."""
    bind(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    require(receipt.get("schema") == "bl.native.host-parts-build" and receipt.get("version") == 1
            and receipt.get("status") == "built-not-executed" and receipt.get("executed") is False
            and receipt.get("source_interpreter") is False and receipt.get("anf_interpreter") is False
            and receipt.get("compile_deadline_seconds") == 120
            and receipt.get("component_byte_limit") == 65536
            and receipt.get("exact_host_concatenation") is True,
            "derived host image lacks its exact bounded ABI partition admission")
    require(receipt["parent_build"] == {"path": str(build_path), "sha256": digest(build_path)}
            and receipt["original_source"] == {"path": str(out / "stage1.scm"), "sha256": stage["source_sha256"]}
            and receipt["original_image"] == {"path": str(out / "stage1"), "sha256": stage["executable_sha256"]}
            and receipt["frozen_host"]["sha256"] == digest(out / "host.scm")
            and receipt["frozen_host"]["whole_unit_sha256"] == stage["units"][0]["sha256"],
            "derived host image selects another original compiler/host checkpoint")
    for name, expected in receipt["inputs"].items():
        bind(path_for(name), expected)
    builder = (base / "build-host-parts.py").resolve()
    require(receipt["inputs"].get(str(builder)) == digest(builder)
            and receipt["sdk_pin"] == json.loads((base / "sdk-pin.json").read_text()),
            "derived host builder or SDK pin changed")
    tools = receipt["tool_identity"]
    require(tools["driver_sha256"] == digest(builder), "derived host recipe driver changed")
    no_inline = receipt.get("no_inline_functions")
    require(type(no_inline) is bool, "derived host optimization choice is ambiguous")
    declaration = "(declare (separate) (safe) (interrupts-enabled)"
    if stage["standard_bindings"]:
        declaration += " (standard-bindings) (extended-bindings)"
    expected_gsc = ["-prelude", declaration + ")"]
    require(receipt["scheme_compiler_flags"] == expected_gsc and tools["gsc_flags"] == expected_gsc,
            "derived host changed separate/safe/interrupt/primitive-binding declarations")
    original_flags = stage["units"][0]["c_flags"]
    roles = ("seed", "values", "leaves", "lazy", "extra", "compiler", "text-ffi")
    names = (*HOST_SOURCES, "host/native-text.scm")
    parts = receipt["host_parts"]
    require(len(parts) == 7, "derived host must retain all seven exact ABI components")
    c_order, object_order, segments = [], [], []
    def record(row):
        path = path_for(row["path"])
        bind(path, row["sha256"])
        return path
    for ordinal, (part, role, name) in enumerate(zip(parts, roles, names)):
        source = base / name
        require(part["ordinal"] == ordinal and part["role"] == role
                and path_for(part["source"]["path"]) == source,
                "derived host component was omitted or reordered")
        record(part["source"])
        expected = (HEADER if ordinal == 0 else b"") + source.read_bytes() + b"\n"
        segment = record(part["segment"])
        require(segment.read_bytes() == expected and part["bytes"] == len(expected) <= 65536,
                "derived host component changed its exact Source bytes")
        segments.append(expected)
        flags = ["-O0" if role == "text-ffi" else "-O1", *original_flags[1:]]
        if role != "text-ffi" and no_inline:
            flags.append("-fno-inline-functions")
        require(part["c_flags"] == flags, "derived host changed its exact C/ABI flags")
        cfile, obj = record(part["c"]), record(part["object"])
        translation = json.loads(record(part["translation_receipt"]).read_text())
        object_receipt = json.loads(record(part["object_receipt"]).read_text())
        require(translation["request"] == {"role": role, "source_sha256": part["segment"]["sha256"], "tools": tools}
                and translation["outputs"] == {str(cfile): part["c"]["sha256"]}
                and object_receipt["request"] == {"translation": translation["request"],
                    "c_sha256": part["c"]["sha256"], "c_flags": flags}
                and object_receipt["outputs"] == {str(obj): part["object"]["sha256"]},
                "derived host component proof does not bind its exact source/tool/flags/output")
        c_order.append(str(cfile))
        object_order.append(str(obj))
    require(b"".join(segments) == prefix, "derived host changed top-level initialization bytes/order")
    tails = receipt["reused_tails"]
    require(len(tails) == len(stage["units"]) - 1, "derived host did not reuse every exact original tail")
    for ordinal, (tail, original) in enumerate(zip(tails, stage["units"][1:]), 1):
        require(tail == {"original_ordinal": ordinal, "source_sha256": original["sha256"],
            "c": {"path": original["c"], "sha256": original["c_sha256"]},
            "object": {"path": original["object"], "sha256": original["object_sha256"]},
            "c_flags": original["c_flags"], "scheme_compiler_flags": original["scheme_compiler_flags"]},
            "derived host changed an original tail ordinal, module name, flags or object")
        c_order.append(str(record(tail["c"])))
        object_order.append(str(record(tail["object"])))
    require(receipt["link_order"] == c_order and receipt["object_order"] == object_order
            and receipt["native_link_flags"] == stage["native_link_flags"]
            and receipt["link_metadata_c_flags"] == original_flags,
            "derived host link/initialization order or native ABI flags differ")
    link_c, link_o = record(receipt["link_metadata"]), record(receipt["link_object"])
    link_translation = json.loads(record(receipt["link_metadata_receipt"]).read_text())
    link_object = json.loads(record(receipt["link_object_receipt"]).read_text())
    native_link = json.loads(record(receipt["native_link_receipt"]).read_text())
    link_request = {"tools": tools, "ordered_c_units": [{"path": name, "sha256": digest(Path(name))} for name in c_order]}
    image = record(receipt["image"])
    require(link_translation["request"] == link_request
            and link_translation["outputs"] == {str(link_c): receipt["link_metadata"]["sha256"]}
            and link_object["request"] == {"link": link_request,
                "c_sha256": receipt["link_metadata"]["sha256"], "c_flags": original_flags}
            and link_object["outputs"] == {str(link_o): receipt["link_object"]["sha256"]}
            and native_link["request"] == {"link": link_request,
                "link_object_sha256": receipt["link_object"]["sha256"],
                "ordered_objects": [{"path": name, "sha256": digest(Path(name))} for name in object_order],
                "link_flags": stage["native_link_flags"]}
            and native_link["outputs"] == {str(image): receipt["image"]["sha256"]},
            "derived host link receipts changed the exact object/order/flags/image recipe")
    with image.open("rb") as stream:
        require(stream.read(4) == b"\x7fELF" and os.access(image, os.X_OK), "derived host image is not an executable ELF")
    return image, {"receipt": {"path": str(receipt_path), "sha256": digest(receipt_path)},
        "image": receipt["image"], "host_component_c_flags": [p["c_flags"] for p in parts],
        "host_source_bytes_and_order_equal": True, "tail_objects_reused": len(tails),
        "fixpoint_qualified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("research/native-seed/out/compiler-closure"))
    parser.add_argument("--evidence", type=Path, default=Path("research/native-seed/evidence/self-emission.json"))
    parser.add_argument("--host-parts-receipt", type=Path,
                        help="admit an explicit same-Source seven-component optimized host image")
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
        if args.host_parts_receipt:
            image, derived = admit_host_parts(path_for(args.host_parts_receipt), bind, path_for,
                                              base, out, stage, build_path, prefix)
            report["derived_native_image"] = derived
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
