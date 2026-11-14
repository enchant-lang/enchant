#!/usr/bin/env python3
"""Qualify an already emitted direct-C scalar unit; never run a BL producer.

Run under the root's sequential cgroup wrapper. This is scalar ABI evidence,
not actor-corpus, compiler-fixpoint or independent-runtime qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time


EXPECTED_CHECKS = [
    "direct-scalar-closure", "direct-scalar-tail", "direct-scalar-loop",
    "direct-scalar-operand-order", "direct-scalar-try",
    "direct-scalar-finally-value", "direct-scalar-map",
    "direct-scalar-truthy-zero", "direct-scalar-nil-list-distinct",
    "direct-scalar-exact-int",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_for(script: Path) -> Path:
    for parent in script.parents:
        if (parent / "research/native-seed/toolchain-pin.json").is_file():
            return parent
    raise RuntimeError("cannot find prototype toolchain pin from qualifier path")


def main() -> int:
    root = root_for(Path(__file__).resolve())
    base = root / "research/native-seed"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=base / "out/direct-scalar")
    parser.add_argument("--host", type=Path, default=base / "out/compiler-closure/host.scm")
    parser.add_argument("--evidence", type=Path, default=base / "evidence/direct-scalar")
    parser.add_argument("--build-timeout", type=int, default=120)
    parser.add_argument("--run-timeout", type=int, default=30)
    args = parser.parse_args()
    out = args.out.resolve()
    host = args.host.resolve()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / "qualification.json"
    # No old green evidence survives an unsuccessful new attempt.
    report_path.unlink(missing_ok=True)
    for name in ("compile.log", "run.log"):
        (evidence / name).unlink(missing_ok=True)
    report = {
        "status": "running", "scope": "direct C scalar ABI over shared Gambit host",
        "independent_runtime": False, "actor_corpus": False,
        "compiler_fixpoint": False, "producer_launched": False, "runs": [],
    }
    before: dict[str, str] = {}

    def write_report() -> None:
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    def unchanged() -> None:
        changed = [name for name, digest in before.items()
                   if not Path(name).is_file() or sha(Path(name)) != digest]
        if changed:
            raise RuntimeError("qualification inputs changed: " + ", ".join(changed))

    def run(label: str, argv: list[str], timeout: int) -> str:
        started = time.monotonic()
        process = subprocess.Popen(argv, cwd=out, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, start_new_session=True)
        timed_out = False
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
            (evidence / (label + ".log")).write_text(output)
            report["runs"].append({"label": label, "argv": argv,
                                   "seconds": round(time.monotonic() - started, 3),
                                   "exit": process.returncode, "interrupted": True})
            write_report()
            raise
        (evidence / (label + ".log")).write_text(output)
        report["runs"].append({"label": label, "argv": argv,
                               "seconds": round(time.monotonic() - started, 3),
                               "exit": process.returncode, "timed_out": timed_out})
        write_report()
        unchanged()
        if timed_out:
            raise RuntimeError(f"{label} exceeded {timeout}s; process group killed")
        if process.returncode:
            raise RuntimeError(f"{label} exited {process.returncode}: {output[-4000:]}")
        return output

    try:
        if not (1 <= args.build_timeout <= 240 and 1 <= args.run_timeout <= 120):
            raise RuntimeError("timeouts must remain within compiler/runtime deadlines")
        tools_path = base / "toolchain-pin.json"
        tools = json.loads(tools_path.read_text())
        gambit = Path(tools["gambit"])
        sdk_pin_path = base / "sdk-pin.json"
        sdk_pin = json.loads(sdk_pin_path.read_text())
        descriptor = Path(sdk_pin["sdk"]) / "artifact.json"
        if sha(descriptor) != sdk_pin["descriptor_sha256"]:
            raise RuntimeError("qualified SDK descriptor identity changed")
        # Snapshot qualification binds the retained artifact; the integration
        # checkout may select a different SDK for unrelated engine work.
        report["sdk_selection"] = "qualified immutable sdk-pin.json artifact"
        program = out / "program.scm"
        control = out / "control.c"
        manifest_path = out / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("schema") != "bl.native.direct-c-unit" or manifest.get("version") != 1:
            raise RuntimeError("not a concrete direct-C unit manifest")
        if manifest.get("scope") != "scalar-abi-smoke":
            raise RuntimeError("qualifier requires the original scalar ABI fixture artifact")
        fixture = Path(manifest["fixture"])
        if not fixture.is_absolute():
            fixture = root / fixture
        if sha(fixture) != manifest.get("fixture-sha256"):
            raise RuntimeError("scalar fixture identity differs from emitted artifact")
        machine = base / "direct/direct-machine.scm"
        header = base / "direct/native-direct.h"
        prefix = host.read_bytes() + b"\n" + machine.read_bytes() + b"\n"
        program_bytes = program.read_bytes()
        if not program_bytes.startswith(prefix):
            raise RuntimeError("scalar artifact has stale host/machine bytes; rerun its producer")
        # C control contains only generated ASCII identifiers/pc edges. JSON's
        # escapes equal the emitter's Scheme string escapes for this payload.
        declaration = "(c-declare " + json.dumps(control.read_text(), ensure_ascii=False) + ")"
        if declaration not in program_bytes.decode():
            raise RuntimeError("separate C control artifact differs from its compiled FFI declaration")
        inputs = [program, control, manifest_path, host, machine, header, fixture,
                  base / "direct/scalar.bl", base / "src/native/c.bl",
                  tools_path, sdk_pin_path, descriptor, Path(__file__).resolve()]
        before.update({str(path): sha(path) for path in inputs})
        report.update({"inputs": before, "sdk": sdk_pin, "tools": tools,
                       "emission_manifest": manifest})
        write_report()
        compiled = out / "program.o1"
        compiled.unlink(missing_ok=True)
        generated = out / "program.c"
        generated.unlink(missing_ok=True)
        options = "-O0 " + shlex.quote("-I" + str(header.parent))
        run("compile", [str(gambit / "bin/gsc"), "-dynamic", "-o", str(compiled),
                        "-cc-options", options, "-ld-options", "-ldl", str(program)],
            args.build_timeout)
        if not compiled.is_file():
            raise RuntimeError("compiler returned success without producing its dynamic unit")
        transcript = run("run", [str(gambit / "bin/gsi"), str(compiled)], args.run_timeout)
        lines = transcript.splitlines()
        passed = [line[5:] for line in lines if line.startswith("PASS ")]
        if passed != EXPECTED_CHECKS:
            raise RuntimeError(f"scalar checks differ: expected {EXPECTED_CHECKS!r}, got {passed!r}")
        if any(line.startswith("FAIL ") for line in lines):
            raise RuntimeError("scalar fixture printed a failed check")
        order = [line for line in lines if line.startswith("SCALAR_ORDER ")]
        if order != ["SCALAR_ORDER first", "SCALAR_ORDER second"]:
            raise RuntimeError(f"operand trace differs: {order!r}")
        if not (lines.index(order[0]) < lines.index(order[1]) <
                lines.index("PASS direct-scalar-operand-order")):
            raise RuntimeError("operand trace happened after its result was checked")
        if lines.count("SCALAR_FINALLY once") != 1:
            raise RuntimeError("finally did not execute exactly once")
        if lines.index("SCALAR_FINALLY once") > lines.index("PASS direct-scalar-finally-value"):
            raise RuntimeError("finally happened after the try result escaped")
        if lines.count("NATIVE_DIRECT_SCALAR_OK") != 1 or lines[-1] != "NATIVE_DIRECT_SCALAR_OK":
            raise RuntimeError("scalar fixture did not finish with its completion marker")
        unchanged()
        artifacts = [compiled, evidence / "compile.log", evidence / "run.log"]
        if generated.is_file():
            artifacts.append(generated)
        report.update({"status": "pass", "checks": passed,
                       "inputs_after": {name: sha(Path(name)) for name in before},
                       "trace": order + ["SCALAR_FINALLY once"],
                       "artifacts": {str(path): {"sha256": sha(path), "bytes": path.stat().st_size}
                                     for path in artifacts}})
        write_report()
        print("DIRECT_SCALAR_QUALIFIED 10 checks; operand order; finally once", flush=True)
        return 0
    except BaseException as error:
        report.update({"status": "fail", "error": str(error)})
        if before:
            report["inputs_after"] = {name: sha(Path(name)) if Path(name).is_file() else None
                                      for name in before}
        write_report()
        print("DIRECT_SCALAR_FAILED " + str(error), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
