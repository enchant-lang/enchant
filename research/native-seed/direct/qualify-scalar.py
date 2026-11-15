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
import re
import shlex
import signal
import subprocess
import sys
import time


EXPECTED_CHECKS = [
    "direct-scalar-closure", "direct-scalar-tail-frame-retention", "direct-scalar-tail", "direct-scalar-loop",
    "direct-scalar-operand-order", "direct-scalar-call-slots", "direct-scalar-try",
    "direct-scalar-finally-value", "direct-scalar-map",
    "direct-scalar-truthy-zero", "direct-scalar-nil-list-distinct",
    "direct-scalar-exact-int", "direct-scalar-raw-primitives",
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
    parser.add_argument("--assembled-host", type=Path,
                        help="admit a prepared full host and replace only the exact original host prefix")
    parser.add_argument("--evidence", type=Path, default=base / "evidence/direct-scalar")
    parser.add_argument("--build-timeout", type=int, default=120)
    parser.add_argument("--run-timeout", type=int, default=30)
    parser.add_argument("--gc-interval", type=int, default=997,
                        help="force GC every N completed C steps; 0 disables the explicit stress reruns")
    args = parser.parse_args()
    out = args.out.resolve()
    host = args.host.resolve()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / "qualification.json"
    # No old green evidence survives an unsuccessful new attempt.
    report_path.unlink(missing_ok=True)
    for name in ("compile.log", "run.log", "scheme-to-c.log", "clang-native.log", "native.log",
                 "llvm-emit.log", "llvm-link.log", "llvm.log", "gc-native.log", "gc-llvm.log"):
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

    def run(label: str, argv: list[str], timeout: int, gc_interval: int = 0,
            fast_mode: bool | None = None) -> str:
        started = time.monotonic()
        environment = os.environ.copy()
        environment.pop("BL_NATIVE_C_GC_INTERVAL", None)
        if gc_interval:
            environment["BL_NATIVE_C_GC_INTERVAL"] = str(gc_interval)
        if fast_mode is not None:
            for name in ("BL_NATIVE_C_NOACTOR_TICK", "BL_NATIVE_C_PURE_BIFS", "BL_NATIVE_C_SYMBOL_MFAS"):
                environment[name] = "1" if fast_mode else "0"
        process = subprocess.Popen(argv, cwd=out, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, start_new_session=True, env=environment)
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
                               "exit": process.returncode, "timed_out": timed_out,
                               "forced_gc_interval": gc_interval})
        write_report()
        unchanged()
        if timed_out:
            raise RuntimeError(f"{label} exceeded {timeout}s; process group killed")
        if process.returncode:
            raise RuntimeError(f"{label} exited {process.returncode}: {output[-4000:]}")
        return output

    fast_witnesses = {}
    report["fast_path_witnesses"] = fast_witnesses
    derived_drivers = []

    def run_scalar(label, unit, interval=0, enabled=True):
        if not args.assembled_host:
            return run(label, [str(gambit / "bin/gsi"), str(unit)], args.run_timeout, interval)
        driver = out / (label + "-fast-path-driver.scm")
        driver.write_text("(load " + json.dumps(str(unit)) + ")\n"
            '(display "NATIVE_DIRECT_FAST_PATHS {\\\"ticks\\\":")\n'
            '(display native-c-noactor-ticks-elided)\n'
            '(display ",\\\"seen\\\":") (display native-c-pure-bif-seen)\n'
            '(display ",\\\"steps\\\":") (display native-c-pure-bif-steps)\n'
            '(display ",\\\"closures\\\":") (display native-c-direct-closure-hits) (display "}\\n")\n')
        derived_drivers.append(driver)
        output = run(label, [str(gambit / "bin/gsi"), str(driver)], args.run_timeout,
                     interval, enabled)
        body, separator, encoded = output.rpartition("NATIVE_DIRECT_FAST_PATHS ")
        if not separator:
            raise RuntimeError(label + " lacks actual fast-path witnesses")
        witness = json.loads(encoded)
        if enabled and not interval:
            if (witness.get("ticks", 0) <= 0 or witness.get("seen") != 23
                    or witness.get("steps", 0) <= 0 or witness.get("closures", 0) <= 0):
                raise RuntimeError(label + " did not execute all guarded BIF, tick and C closure paths")
        elif witness != {"ticks": 0, "seen": 0, "steps": 0, "closures": 0}:
            raise RuntimeError(label + " failed to retain the original path when disabled or under GC stress")
        fast_witnesses[label] = witness
        return body

    try:
        if not (1 <= args.build_timeout <= 120 and 1 <= args.run_timeout <= 30):
            raise RuntimeError("timeouts must remain within the 120s compiler / 30s runtime deadlines")
        if args.gc_interval < 0:
            raise RuntimeError("GC interval must be zero or a positive exact integer")
        tools_path = base / "toolchain-pin.json"
        tools = json.loads(tools_path.read_text())
        gambit = Path(tools["gambit"])
        clang = Path(tools["clang"]) / "bin/clang"
        build_script = gambit / "gambit/bin/gambuild-C"
        public_header = gambit / "gambit/include/gambit.h"
        definitions = re.findall(r'^DEFS_DYN="([^"\n]*)"$', build_script.read_text(), re.MULTILINE)
        if len(definitions) != 1 or "$" in definitions[0]:
            raise RuntimeError("pinned Gambit dynamic ABI definition is not a single literal")
        dynamic_defines = shlex.split(definitions[0])
        expected_defines = ["-D___SINGLE_HOST", "-D___TRUST_C_TCO",
                            "-D___CAN_IMPORT_CLIB_DYNAMICALLY",
                            "-D___CAN_IMPORT_SETJMP_DYNAMICALLY", "-D___DYNAMIC"]
        if dynamic_defines != expected_defines:
            raise RuntimeError(f"pinned public dynamic ABI changed: {dynamic_defines!r}")
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
        if manifest.get("schema") != "bl.native.direct-c-unit" or manifest.get("version") != 1 or manifest.get("action-abi") != 2:
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
        if re.findall(r'^#define BL_NATIVE_DIRECT_ABI ([0-9]+)$', header.read_text(), re.MULTILINE) != ['2']:
            raise RuntimeError("scalar requires the exact action ABI2 header")
        if not control.read_text().startswith('#include "native-direct.h"\n#if !defined(BL_NATIVE_DIRECT_ABI) || BL_NATIVE_DIRECT_ABI != 2\n'):
            raise RuntimeError("scalar C control lacks its action ABI2 guard")
        if program.read_text().splitlines().count('(native-c-require-action-abi! 2)') != 1:
            raise RuntimeError("scalar wrapper lacks its action ABI2 guard")
        report.update({"action-abi": 2, "header-action-abi": 2, "header_sha256": sha(header)})
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
                  tools_path, sdk_pin_path, descriptor, build_script, public_header, Path(__file__).resolve()]
        capsules = manifest.get("producer-capsules", [])
        if (len(capsules) != 2 or {row["path"] for row in capsules} != {
                "priv/lib/js/actor.bl", "research/native-seed/src/native/artifact-capsules.bl"}):
            raise RuntimeError("scalar capsule provenance is incomplete")
        for row in capsules:
            path = Path(row["path"])
            if not path.is_absolute():
                path = root / path
            if sha(path) != row["sha256"]:
                raise RuntimeError("scalar capsule Source identity changed: " + str(path))
            inputs.append(path)
        if args.assembled_host:
            directory = args.assembled_host.resolve()
            aggregate, preparation, ledger = (directory / name for name in
                ("host.scm", "preparation.json", "host.components.json"))
            prepared = json.loads(preparation.read_text())
            components = json.loads(ledger.read_text())
            if (prepared.get("status") != "assembled-not-executed"
                    or prepared.get("action-abi") != 2
                    or prepared.get("header_sha256") != sha(header)
                    or components.get("schema") != "bl.native.direct-host"
                    or components.get("action-abi") != 2
                    or components.get("source_sha256") != sha(aggregate)
                    or prepared.get("host_sha256") != sha(aggregate)):
                raise RuntimeError("optimized scalar requires an exact assembled ABI2 host")
            paths = {}
            for name, digest in prepared["inputs"].items():
                path = Path(name)
                if sha(path) != digest:
                    raise RuntimeError("assembled host input changed: " + name)
                paths.setdefault(digest, path.read_bytes())
                inputs.append(path)
            rows = components["components"]
            if (rows[0] != {"role": "frozen-host", "sha256": sha(host)}
                    or rows[-1]["role"] != "pinned-compiler-configuration"
                    or len({row["role"] for row in rows}) != len(rows)
                    or {"role": "direct-machine", "sha256": sha(machine)} not in rows):
                raise RuntimeError("assembled host does not retain the exact scalar value/machine host")
            body = aggregate.read_bytes()
            offset = 0
            for row in rows[:-1]:
                data = paths.get(row["sha256"])
                if data is None or body[offset:offset + len(data) + 1] != data + b"\n":
                    raise RuntimeError("assembled component order or bytes differ: " + row["role"])
                offset += len(data) + 1
            if (body[-1:] != b"\n" or hashlib.sha256(body[offset:-1]).hexdigest() != rows[-1]["sha256"]):
                raise RuntimeError("assembled configuration identity differs")
            # Keep the canonical emitted program immutable. Only its already
            # verified host prefix is replaced in a separately retained file.
            variant = out / "assembled"
            variant.mkdir(exist_ok=True)
            actual_program = variant / "program.scm"
            actual_program.write_bytes(body + b"\n" + program_bytes[len(prefix):])
            if actual_program.read_text().count(declaration) != 1:
                raise RuntimeError("assembled scalar variant changed emitted C control")
            inputs.extend([aggregate, preparation, ledger, actual_program,
                           base / "direct/prepare-host.py"])
            report["assembled_host"] = {"path": str(directory), "sha256": sha(aggregate),
                "program_sha256": sha(actual_program), "source_anf_control_changed": False,
                "configuration": prepared["optional_extensions"]}
            if prepared["optional_extensions"] != {"noactor_tick_opt_in": True, "pure_bif_opt_in": True,
                                                   "symbol_mfa_opt_in": True}:
                raise RuntimeError("assembled scalar qualification requires both explicit fast-path opt-ins")
            program = actual_program
        before.update({str(path): sha(path) for path in inputs})
        report.update({"inputs": before, "sdk": sdk_pin, "tools": tools,
                       "emission_manifest": manifest})
        write_report()
        compiled = out / "program.o1"
        compiled.unlink(missing_ok=True)
        generated = out / "program.c"
        reference = out / "program.gsc-dynamic-reference.c"
        if generated.is_file():
            old = generated.read_text()
            if re.findall(r'^#define ___LINKER_ID ([^\s]+)\s*$', old, re.MULTILINE) == ["___LNK_program_2e_o1"]:
                reference.write_bytes(generated.read_bytes())
        if reference.is_file():
            report["observed_gsc_dynamic_startup"] = {"path": str(reference), "sha256": sha(reference),
                                                       "symbol": "___LNK_program_2e_o1"}
        generated.unlink(missing_ok=True)
        # gsc only emits C. Its bundled GCC exceeded the existing 2 GiB cap;
        # the pinned Clang compiles the same generated C under unchanged caps.
        run("scheme-to-c", [str(gambit / "bin/gsc"), "-c", "-o", str(generated), str(program)],
            args.build_timeout)
        raw = generated.read_text()
        linker = list(re.finditer(r'^#define ___LINKER_ID ([^\s]+)[ \t]*$', raw, re.MULTILINE))
        if len(linker) != 1 or linker[0].group(1) != "___LNK_program":
            raise RuntimeError("gsc -c did not emit the expected unique program startup symbol")
        if raw.count(control.read_text()) != 1:
            raise RuntimeError("gsc emitted C does not contain exactly the unchanged BL C control graph")
        match = linker[0]
        replacement = "#define ___LINKER_ID ___LNK_program_2e_o1"
        adapted_text = raw[:match.start()] + replacement + raw[match.end():]
        adapted = out / "program.dynamic.c"
        adapted.write_text(adapted_text)
        if adapted_text.count(control.read_text()) != 1:
            raise RuntimeError("startup adaptation changed BL control")
        report["startup_adapter"] = {"kind": "Gambit public dynamic loader basename encoding",
            "from": "___LNK_program", "to": "___LNK_program_2e_o1", "replacements": 1,
            "raw_c_sha256": sha(generated), "adapted_c_sha256": sha(adapted),
            "bl_control_sha256": sha(control), "dynamic_defines": dynamic_defines,
            "public_build_script": str(build_script)}
        flags = ["-O0", "-fwrapv", "-fno-strict-aliasing", "-fno-trapping-math", "-fno-math-errno",
                 "-fPIC", "-fno-common", *dynamic_defines,
                 "-I" + str(public_header.parent), "-I" + str(header.parent)]
        run("clang-native", [str(clang), *flags, "-shared", "-rdynamic", str(adapted),
                             "-ldl", "-lm", "-o", str(compiled)], args.build_timeout)
        if not compiled.is_file():
            raise RuntimeError("compiler returned success without producing its dynamic unit")
        transcript = run_scalar("native", compiled)
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
        call_trace = [line for line in lines if line.startswith("SCALAR_CALL ")]
        expected_call_trace = ["SCALAR_CALL " + label for label in (
            "zero-callee", "callee", "first", "second", "third", "callee-throws",
            "throw-callee", "before-throw", "argument-throws", "arity-callee",
            "arity-first", "arity-second")]
        if call_trace != expected_call_trace:
            raise RuntimeError(f"finite-call operand/exception trace differs: {call_trace!r}")
        if not all(lines.index(line) < lines.index("PASS direct-scalar-call-slots") for line in call_trace):
            raise RuntimeError("finite-call effects happened after their result escaped")
        if lines.count("SCALAR_FINALLY once") != 1:
            raise RuntimeError("finally did not execute exactly once")
        if lines.index("SCALAR_FINALLY once") > lines.index("PASS direct-scalar-finally-value"):
            raise RuntimeError("finally happened after the try result escaped")
        if lines.count("NATIVE_DIRECT_SCALAR_OK") != 1 or lines[-1] != "NATIVE_DIRECT_SCALAR_OK":
            raise RuntimeError("scalar fixture did not finish with its completion marker")
        # The LLVM route derives from exactly the SAME adapted C, not from a
        # separately emitted program. Preserve the .o1 basename for its ABI id.
        llvm_dir = out / "llvm"
        llvm_dir.mkdir(exist_ok=True)
        llvm_ir = llvm_dir / "program.ll"
        llvm_unit = llvm_dir / "program.o1"
        llvm_ir.unlink(missing_ok=True)
        llvm_unit.unlink(missing_ok=True)
        adapted_hash = sha(adapted)
        run("llvm-emit", [str(clang), *flags, "-S", "-emit-llvm", "-fno-discard-value-names",
                          str(adapted), "-o", str(llvm_ir)], args.build_timeout)
        if sha(adapted) != adapted_hash:
            raise RuntimeError("adapted C changed during LLVM lowering")
        run("llvm-link", [str(clang), "-O0", "-fPIC", "-shared", "-rdynamic", str(llvm_ir),
                          "-ldl", "-lm", "-o", str(llvm_unit)], args.build_timeout)
        llvm_transcript = run_scalar("llvm", llvm_unit)
        if llvm_transcript != transcript:
            raise RuntimeError("native C and LLVM scalar transcripts differ")
        if args.assembled_host:
            if fast_witnesses["native"] != fast_witnesses["llvm"]:
                raise RuntimeError("native C and LLVM fast-path witnesses differ")
            for label, unit in (("off-native", compiled), ("off-llvm", llvm_unit)):
                if run_scalar(label, unit, enabled=False) != transcript:
                    raise RuntimeError(label + " changed the canonical scalar transcript")
        gc_artifacts = []
        gc_witnesses = {}
        for label, unit in (("gc-native", compiled), ("gc-llvm", llvm_unit)) if args.gc_interval else ():
            driver = out / (label + ".scm")
            driver.write_text("(load " + json.dumps(str(unit), ensure_ascii=False) + ")\n"
                "(if (not (= native-c-gc-interval " + str(args.gc_interval) + ")) (error \"GC interval mismatch\"))\n"
                "(if (not (> native-c-forced-gc-count 0)) (error \"no forced collections observed\"))\n"
                "(if (not (= native-c-forced-gc-count (quotient native-c-step-count native-c-gc-interval))) (error \"GC count mismatch\"))\n"
                "(display \"NATIVE_DIRECT_GC {\\\"steps\\\":\") (display native-c-step-count)\n"
                "(display \",\\\"collections\\\":\") (display native-c-forced-gc-count)\n"
                "(display \",\\\"interval\\\":\") (display native-c-gc-interval) (display \"}\\n\")\n")
            gc_output = run_scalar(label, driver, args.gc_interval)
            body, separator, witness = gc_output.rpartition("NATIVE_DIRECT_GC ")
            if not separator or body != transcript:
                raise RuntimeError(label + " changed the exact scalar transcript")
            observation = json.loads(witness)
            if (observation.get("interval") != args.gc_interval or observation.get("collections", 0) <= 0
                    or observation["collections"] != observation["steps"] // args.gc_interval):
                raise RuntimeError(label + " did not witness the requested collections")
            gc_witnesses[label] = observation
            gc_artifacts.extend([driver, evidence / (label + ".log")])
        if args.gc_interval and gc_witnesses["gc-native"] != gc_witnesses["gc-llvm"]:
            raise RuntimeError("native C and LLVM GC witnesses differ")
        unchanged()
        artifacts = [compiled, generated, adapted, llvm_ir, llvm_unit, *gc_artifacts, *derived_drivers,
                     *[evidence / (label + ".log") for label in
                       ("scheme-to-c", "clang-native", "native", "llvm-emit", "llvm-link", "llvm")]]
        if args.assembled_host:
            artifacts.extend(evidence / (label + ".log") for label in ("off-native", "off-llvm"))
        if reference.is_file():
            artifacts.append(reference)
        report.update({"status": "pass", "checks": passed,
                       "inputs_after": {name: sha(Path(name)) for name in before},
                       "trace": order + call_trace + ["SCALAR_FINALLY once"], "llvm_transcript_equal": True,
                       "gc_stress": {"enabled": bool(args.gc_interval), "interval": args.gc_interval,
                                     "witnesses": gc_witnesses, "recompiled": False},
                       "fast_path_witnesses": fast_witnesses,
                       "artifacts": {str(path): {"sha256": sha(path), "bytes": path.stat().st_size}
                                     for path in artifacts}})
        write_report()
        print(f"DIRECT_SCALAR_QUALIFIED C=LLVM; {len(passed)} checks; operand order; finally once", flush=True)
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
