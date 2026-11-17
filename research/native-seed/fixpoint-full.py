#!/usr/bin/env python3
"""Native source bootstrap with bounded real Scheme -> C translation units.

Stage zero is an already admitted canonical BL closure. GSI only reads/writes
top-level Scheme forms for splitting; compiled BL bodies are never interpreted.
Every compiler/C job retains a 120-second deadline. Objects are reused only with
the same source, ordinal, tools, public Gambit ABI and verified output hashes.
Full qualification additionally runs the original actor corpus against each
stage's actual core/rt and a fresh, hash-bound JavaScript oracle.
"""
from __future__ import annotations

import argparse
import ast
import fcntl
import uuid
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

HEADER = b";; BL native compiler. Generated from canonical BL source.\n"
ENTRY = b"(native-main (native-command-line))\n"
TARGET = 256 * 1024
HARD = 1024 * 1024
COMPILE_DEADLINE = 120
STANDARD_BINDING_PRELUDE = "(declare (standard-bindings) (extended-bindings))"
BUDGETS = ("default", "17", "41")
ORIGINAL = "5f2ad8223fd9f053157b65266d3ee14e7fe8567b6196a78ed7ac955132b9a5c5"
ZERO = {"procs": 0, "monitors": 0, "tables": 0, "names": 0, "table_names": 0,
        "runnable": 0, "input_sink": None, "critical": 0, "errors": 0}


CLOCK_MODEL = {"name": "virtual-turn-ms-v1", "tick-ms": 1,
               "event": "completed-host-turn", "idle-progress": "existing-host-wait", "real-time": False}


def validate_native_clock(witness):
    clock = witness.get("clock", {})
    if clock.get("model") != "virtual-turn-ms-v1" or clock.get("tick_ms") != 1:
        raise RuntimeError("native corpus lacks its declared deterministic runnable-progress clock")
    for name in ("completed_turns", "yield_turns", "turn_ms", "elapsed_ms"):
        if type(clock.get(name)) is not int or clock[name] <= 0:
            raise RuntimeError("native corpus clock lacks positive actual " + name)
    if (clock["yield_turns"] > clock["completed_turns"]
            or clock["turn_ms"] != clock["completed_turns"] * clock["tick_ms"]
            or clock["elapsed_ms"] < clock["turn_ms"]):
        raise RuntimeError("native corpus completed/yield turn time progress is inconsistent")
    return clock


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def key(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def compiler_recipe_identity(source_path: Path) -> dict:
    # Hash actual compiler code independently from orchestration/reporting.
    # Whole-driver bytes remain a bound input/provenance record.
    names = ("digest", "key", "save", "run", "split_source", "unit_cache_request", "cached_phase", "compile_native")
    tree = ast.parse(source_path.read_text(), filename=str(source_path))
    functions = []
    for name in names:
        found = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
        if len(found) != 1 or not isinstance(found[0], ast.FunctionDef):
            raise RuntimeError("compiler recipe requires exactly one synchronous function: " + name)
        function = found[0]
        if name == "compile_native":
            # This selector changes only the already-bound object argv and
            # output/proof variant names. Normalize exactly this statement so
            # unchanged translations and O0 objects retain their prior recipe.
            # Full driver bytes and actual selected flags remain bound.
            selector = ast.parse('if ordinal == 0 and args.host_no_inline_functions:\n    object_flags.append("-fno-inline-functions")\n    obj = directory / (stem + ".O1.noinline.o")\n    optimization = "1.noinline"').body[0]
            selector_dump = ast.dump(selector, annotate_fields=True, include_attributes=False)
            removed = []
            class ObjectFlagSelector(ast.NodeTransformer):
                def visit_If(self, node):
                    if ast.dump(node, annotate_fields=True, include_attributes=False) == selector_dump:
                        removed.append(node)
                        return None
                    return self.generic_visit(node)
            function = ObjectFlagSelector().visit(function)
            if len(removed) != 1:
                raise RuntimeError("expected exactly one reviewed host object flag selector")
        functions.append([name, ast.dump(function, annotate_fields=True, include_attributes=False)])
    constants = {"header": HEADER.decode(), "entry": ENTRY.decode(),
                 "unit_target_bytes": TARGET, "unit_hard_bytes": HARD,
                 "compile_deadline_seconds": COMPILE_DEADLINE,
                 "standard_binding_prelude": STANDARD_BINDING_PRELUDE}
    payload = {"schema": "bl.native.python-compiler-recipe", "version": 1,
               "functions": functions, "constants": constants}
    return {"schema": payload["schema"], "version": 1, "sha256": key(payload),
            "functions": list(names), "constants": constants,
            "object_flag_selector": {"normalization": "host-O1-no-inline-only-v1",
                "actual_flags_bound_in_object_request": True,
                "full_driver_bound_in_report": True}}


def split_source(source: Path, *, host_unit: bytes, host_scheme: Path, gsi: Path, splitter: Path,
                 out: Path, run):
    """Split one emitted stage into the frozen host unit plus content-cut form
    units (split-top-level.scm). Each unit is keyed later by its own bytes."""
    body = source.read_bytes()
    if not body.startswith(host_unit):
        raise RuntimeError("native stage does not begin with the exact frozen host source")
    request = {"source_sha256": digest(source), "host_sha256": digest(host_scheme),
               "reader_sha256": digest(gsi), "splitter_sha256": digest(splitter),
               "target": TARGET, "hard": HARD}
    folder = out / "native-split" / key(request)
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / "manifest.json"
    if manifest.is_file():
        old = json.loads(manifest.read_text())
        rows = old.get("units", [])
        if (old.get("schema") == "bl.native.scheme-units" and old.get("version") == 1
                and old.get("request") == request and len(rows) >= 2
                and rows[0].get("file") == "host.scm"
                and rows[0].get("sha256") == hashlib.sha256(host_unit).hexdigest()
                and [r.get("file") for r in rows[1:]] == [f"forms-{i}.scm" for i in range(len(rows) - 1)]
                and all((folder / row["file"]).is_file()
                        and 0 < (folder / row["file"]).stat().st_size == row["bytes"] <= HARD
                        and digest(folder / row["file"]) == row["sha256"]
                        and (row["bytes"] <= TARGET or row.get("indivisible_ffi_host")
                             or (row.get("forms") == 1 and row.get("oversized_single_form"))) for row in rows)):
            return folder, old
    host_path, tail = folder / "host.scm", folder / "tail.scm"
    host_path.write_bytes(host_unit)
    tail.write_bytes(body[len(host_unit):])
    job = folder / "split.scm"
    job.write_text("(define split-input " + json.dumps(str(tail)) + ")\n"
        + "(define split-output " + json.dumps(str(folder)) + ")\n"
        + f"(define split-target {TARGET})\n(define split-hard {HARD})\n"
        + splitter.read_text())
    # Old partially split outputs are local generated files only.
    for path in folder.glob("forms-*.scm"):
        path.unlink()
    output = run("split-" + source.stem, [gsi, job])
    units = [{"file": "host.scm", "bytes": len(host_unit), "forms": None,
              "indivisible_ffi_host": True, "oversized_single_form": False,
              "sha256": digest(host_path)}]
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 5 or fields[0] != "CHUNK":
            raise RuntimeError("unexpected top-level splitter output: " + line)
        _, filename, forms, size, oversized = fields
        path = folder / filename
        size, forms, oversized = int(size), int(forms), int(oversized)
        if (path.parent != folder or not filename.startswith("forms-")
                or path.stat().st_size != size or not 0 < size <= HARD or forms <= 0
                or oversized not in (0, 1) or (size > TARGET and (forms != 1 or not oversized))):
            raise RuntimeError("invalid bounded Scheme unit record: " + line)
        units.append({"file": filename, "bytes": size, "forms": forms,
                      "indivisible_ffi_host": False, "oversized_single_form": bool(oversized),
                      "sha256": digest(path)})
    if len(units) < 2:
        raise RuntimeError("splitter omitted compiler bodies and entry")
    result = {"schema": "bl.native.scheme-units", "version": 1, "request": request,
              "transport": "Gambit read/write; forms never evaluated; original top-level order",
              "units": units}
    save(manifest, result)
    return folder, result


def unit_cache_request(row: dict, ordinal: int, tool_identity: dict) -> dict:
    """A unit's Scheme -> C identity is its own bytes, its role and the tools.
    The ordinal and the neighbours are not part of it: a changed unit never
    perturbs another's key. Gambit's module name comes from the stem, which is
    derived from this key, and the link table (gsc -link) is built separately
    from the ordered C units."""
    return {"source_sha256": row["sha256"], "role": "host" if ordinal == 0 else "forms",
            "tools": tool_identity}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--actor-body", type=Path)
    parser.add_argument("--actor-manifest", type=Path,
                        help="explicit fresh actor capture; its unchanged body may live in the historical directory")
    parser.add_argument("--stage1-receipt", type=Path,
                        help="reuse an exact already-built native stage1 checkpoint after strict hash/ABI admission")
    parser.add_argument("--self-emission-receipt", type=Path,
                        help="reuse an actual successful focused stage1 self-emission with unchanged image/bundle/host/log proofs")
    parser.add_argument("--actor-oracle", type=Path)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--host-optimization", type=int, choices=(0, 1), default=0,
                        help="Clang optimization level for the indivisible ordinal-zero host only")
    parser.add_argument("--host-no-inline-functions", action="store_true",
                        help="add -fno-inline-functions only to host -O1; reuse all unchanged O0 units")
    parser.add_argument("--standard-bindings", action="store_true",
                        help="assert immutable stock Gambit primitive bindings during Scheme -> C only")
    parser.add_argument("--compile-stage1-only", action="store_true",
                        help="checkpoint the real native stage1 image; never qualify a fixpoint")
    parser.add_argument("--compile-stage1-actors-only", action="store_true",
                        help="build exact stage1 core + original actor body; never execute or qualify")
    parser.add_argument("--actor-diagnostic-prefix", type=Path,
                        help="observational prefix for a separate NONQUALIFIED actor image")
    args = parser.parse_args()
    if args.host_no_inline_functions and args.host_optimization != 1:
        parser.error("--host-no-inline-functions requires --host-optimization 1")
    if args.actor_diagnostic_prefix and not args.compile_stage1_actors_only:
        parser.error("--actor-diagnostic-prefix requires --compile-stage1-actors-only")
    if args.actor_diagnostic_prefix:
        args.actor_diagnostic_prefix = args.actor_diagnostic_prefix.resolve()
    if args.compile_stage1_only and args.compile_stage1_actors_only:
        parser.error("select only one stage1 checkpoint mode")
    if args.compile_stage1_actors_only and not args.actor_manifest:
        parser.error("--compile-stage1-actors-only requires --actor-manifest")
    if args.self_emission_receipt and not args.stage1_receipt:
        parser.error("--self-emission-receipt requires --stage1-receipt")
    # This is a compiler declaration, not an edit to the original Source or
    # Scheme artifact. Keep the existing separate/safe/interrupt/tail policies.
    gsc_flags = ["-prelude", STANDARD_BINDING_PRELUDE] if args.standard_bindings else []
    args.corpus = args.corpus.resolve()
    if args.actor_body:
        args.actor_body = args.actor_body.resolve()
    if args.actor_oracle:
        args.actor_oracle = args.actor_oracle.resolve()
    if not 1 <= args.timeout <= 240:
        raise RuntimeError("native self-compilation retains its 240-second deadline")
    if not (args.compile_stage1_only or args.compile_stage1_actors_only) and (not args.actor_manifest or not args.actor_oracle):
        raise RuntimeError("full fixpoint requires --actor-manifest and --actor-oracle")
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    evidence = out / "full-fixpoint.json"
    progress_path = out / "full-native-build.json"
    lock = (out / "full-fixpoint.lock").open("a")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    attempts = out / "full-fixpoint-attempts" / uuid.uuid4().hex
    attempts.mkdir(parents=True, exist_ok=False)
    if evidence.exists():
        shutil.copy2(evidence, attempts / "previous-full-fixpoint.json")
    def terminate(signum, frame):
        raise InterruptedError("full fixpoint received signal " + str(signum))
    previous_term = signal.signal(signal.SIGTERM, terminate)
    here = Path(__file__).resolve()
    splitter = here.with_name("split-top-level.scm")
    base = root / "research/native-seed"
    inputs: dict[str, str] = {}
    runs, builds = [], []
    actor_capture = None
    compiler_recipe = None
    resumed_stage1 = None
    self_emissions, source_results = [], {}

    def path_for(name: str) -> Path:
        path = Path(name)
        return path if path.is_absolute() else root / path

    def bind(path: Path, expected: str | None = None) -> str:
        path = path.resolve()
        actual = digest(path)
        if expected is not None and actual != expected:
            raise RuntimeError("input identity differs: " + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError("input changed during admission: " + str(path))
        inputs[str(path)] = actual
        return actual

    def unchanged() -> None:
        for name, expected in inputs.items():
            if not Path(name).is_file() or digest(Path(name)) != expected:
                raise RuntimeError("native bootstrap input changed: " + name)

    def progress(status="running", error=None) -> None:
        save(progress_path, {"schema": "bl.native.full-bounded-build", "version": 1,
                            "status": status, "error": error, "inputs": inputs,
                            "unit_target_bytes": TARGET, "unit_hard_bytes": HARD,
                            "compile_deadline_seconds": COMPILE_DEADLINE,
                            "host_optimization": args.host_optimization,
                            "host_no_inline_functions": args.host_no_inline_functions,
                            "standard_bindings": args.standard_bindings,
                            "scheme_compiler_flags": gsc_flags,
                            "builds": builds, "runs": runs, "actor_capture": actor_capture,
                            "driver_sha256": digest(here), "compiler_recipe": compiler_recipe})

    def run(label, argv, *, cwd=out, timeout=COMPILE_DEADLINE, env=None):
        argv = [str(x) for x in argv]
        started = time.monotonic()
        log = out / (label + ".log")
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        timed_out = False
        try:
            output, _ = process.communicate(timeout=timeout)
        except BaseException as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            log.write_text(output)
            runs.append({"label": label, "argv": argv, "seconds": round(time.monotonic() - started, 3),
                         "exit": process.returncode, "timeout": timed_out, "log_sha256": digest(log)})
            progress()
            raise
        log.write_text(output)
        runs.append({"label": label, "argv": argv, "seconds": round(time.monotonic() - started, 3),
                     "exit": process.returncode, "timeout": timed_out, "log_sha256": digest(log)})
        progress()
        if process.returncode:
            raise RuntimeError(f"{label}: exit {process.returncode}\n{output[-5000:]}")
        print(label, "PASS", flush=True)
        return output

    try:
        for path in (here, splitter, base / "toolchain-pin.json", base / "sdk-pin.json",
                     out / "stage1.scm", out / "prelude.scm", out / "bundle.scm",
                     out / "host.scm", out / "identity.json", out / "chunk-export.json", args.corpus):
            bind(path)
        tools = json.loads((base / "toolchain-pin.json").read_text())
        gambit = Path(tools["gambit"])
        gsc, gsi = gambit / "bin/gsc", gambit / "bin/gsi"
        clang = Path(tools["clang"]) / "bin/clang"
        for path in (gsc, gsi, clang, gambit / "gambit/include/gambit.h", gambit / "gambit/lib/libgambit.so"):
            bind(path)
        pin = json.loads((base / "sdk-pin.json").read_text())
        descriptor = Path(pin["sdk"]) / "artifact.json"
        bind(descriptor, pin["descriptor_sha256"])
        if json.loads(descriptor.read_text())["source"] != pin["source"]:
            raise RuntimeError("qualified SDK source differs")
        export = json.loads((out / "chunk-export.json").read_text())
        if (export.get("schema") != "bl.native.chunk-export" or export.get("version") != 2
                or export["emission_inputs"]["sdk_descriptor_sha256"] != pin["descriptor_sha256"]):
            raise RuntimeError("stage zero lacks the qualified SDK-bound chunk export")
        bind(out / "prelude.scm", export["prelude_sha256"])
        bind(out / "host.scm", export["inputs"]["host_sha256"])
        if (out / "stage1.scm").read_bytes() != (out / "prelude.scm").read_bytes() + ENTRY:
            raise RuntimeError("stage1 differs from exact admitted prelude and compiler entry")
        host = (out / "host.scm").read_bytes()
        host_unit = HEADER + host + b"\n"
        if len(host_unit) > HARD:
            raise RuntimeError("indivisible C FFI host exceeds 1MiB; explicit ABI partition required")
        flags = ["-O0", "-fwrapv", "-fno-strict-aliasing", "-fPIC", "-pthread", "-D___SINGLE_HOST",
                 "-D___TRUST_C_TCO", "-D___CAN_IMPORT_CLIB_DYNAMICALLY",
                 "-D___CAN_IMPORT_SETJMP_DYNAMICALLY", "-I" + str(gambit / "gambit/include")]
        link_flags = [str(gambit / "gambit/lib/libgambit.so"), "-pthread", "-ldl", "-lm",
                      "-Wl,-rpath," + str(gambit / "gambit/lib")]
        compiler_recipe = compiler_recipe_identity(here)
        tool_identity = {"compiler_recipe": compiler_recipe["sha256"], "splitter": digest(splitter), "flags": flags,
                         "scheme_compiler_flags": gsc_flags,
                         "link_flags": link_flags, "toolchain": tools,
                         "compiler_environment_sha256": key({name: value for name, value in os.environ.items()
                             if name.startswith(("NIX_", "GAMBIT")) or name in
                             ("PATH", "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH", "SDKROOT")}),
                         "tools": {str(p): digest(p) for p in (gsc, gsi, clang,
                                      gambit / "gambit/include/gambit.h", gambit / "gambit/lib/libgambit.so")}}
        actor_results = {}
        oracle = None
        if args.actor_body:
            bind(args.actor_body)
        if args.actor_diagnostic_prefix:
            bind(args.actor_diagnostic_prefix)
        if args.actor_manifest:
            manifest_path = args.actor_manifest.resolve()
            captured = json.loads(manifest_path.read_text())
            recorded_body = path_for(captured["body"]["path"]).resolve()
            if args.actor_body and args.actor_body != recorded_body:
                raise RuntimeError("explicit actor body differs from the supplied manifest")
            args.actor_body = recorded_body
            bind(manifest_path)
            captured = json.loads(manifest_path.read_text())
            captured_link = captured["link"]
            if (captured.get("schema") != "bl.native.original-actor-corpus" or captured.get("version") != 1
                    or captured.get("target") != "scheme" or captured.get("assertion-adaptation") != "none"
                    or captured.get("source-path-adaptation") != "none"
                    or captured["application"] != {"path": "research/js-actors/test.bl", "sha256": ORIGINAL}
                    or captured_link["sdk-pin"] != pin or captured_link["runtime-definitions"] != 202
                    or len(captured_link["emitted-bindings"]) != 405
                    or len(set(captured_link["emitted-bindings"])) != 405
                    or captured_link.get("helper-namespaces") != []
                    or captured_link.get("source-interpreter") is not False
                    or captured["body"]["sha256"] != "4f97857ad1b357fa3c962e58e497fa84b02d43c1fabef3e7a924fa5b3e902a22"
                    or captured.get("clock-model") != CLOCK_MODEL or captured.get("clock") != "virtual-turn-ms-v1"
                    or captured_link.get("source-frames?") is not True
                    or path_for(captured["body"]["path"]).resolve() != args.actor_body
                    or path_for(captured_link["prelude"]["path"]).resolve() != (out / "prelude.scm").resolve()
                    or captured_link["prelude"]["sha256"] != digest(out / "prelude.scm")):
                raise RuntimeError("actor checkpoint must use the complete exact original capture and this stage1 core")
            for record in [captured["application"], captured["runtime"], captured["body"], captured["artifact"], captured["anf"],
                           *captured["inputs"], captured_link["closure-manifest"], captured_link["prelude"],
                           captured_link["links"], captured_link["host-link"],
                           *captured_link["host-extensions"], *captured_link["compile-time-providers"]]:
                bind(path_for(record["path"]), record["sha256"])
            if path_for(captured_link["closure-manifest"]["path"]).resolve() != (out / "partition.json").resolve():
                raise RuntimeError("actor manifest selects another exact compiler closure")
            if path_for(captured["artifact"]["path"]).read_bytes() != (out / "prelude.scm").read_bytes() + b"\n" + args.actor_body.read_bytes():
                raise RuntimeError("actor checkpoint body is not the unchanged suffix of its exact captured core")
            actor_capture = {"manifest": {"path": str(manifest_path), "sha256": digest(manifest_path)},
                             "body": {"path": str(args.actor_body), "sha256": digest(args.actor_body)},
                             "runtime_definitions": 202, "source_assertion_adaptation": "none",
                             "clock_model": captured["clock-model"],
                             "anf": captured["anf"], "link": captured_link, "bindings": 405}
        if args.actor_oracle and not args.compile_stage1_only:
            bind(args.actor_oracle)
            oracle = json.loads(args.actor_oracle.read_text())
            if (oracle.get("schema") != "bl.native.original-actor-oracle" or oracle.get("version") != 1
                    or oracle.get("status") != "complete" or oracle.get("sdk-pin") != pin
                    or oracle.get("target") != "javascript" or oracle.get("native-execution") is not False
                    or oracle.get("clock-model") != CLOCK_MODEL
                    or oracle["application"] != {"path": "research/js-actors/test.bl", "sha256": ORIGINAL}
                    or set(oracle["budgets"]) != set(BUDGETS)):
                raise RuntimeError("actor oracle is not the complete freshly rebuilt original-source baseline")
            if path_for(oracle["body"]["path"]).resolve() != args.actor_body.resolve():
                raise RuntimeError("actor body path differs from oracle")
            if any(oracle[name] != captured[name] for name in ("application", "runtime", "body")):
                raise RuntimeError("fresh native capture differs from portable JS oracle Source/body identities")
            for record in (oracle["application"], oracle["runtime"], oracle["body"], oracle["js-qualification"]):
                bind(path_for(record["path"]), record["sha256"])
            for name, sha in oracle["inputs"].items():
                bind(path_for(name), sha)
            for budget in BUDGETS:
                expected = oracle["budgets"][budget]
                bind(path_for(expected["js_log"]["path"]), expected["js_log"]["sha256"])
                baseline = observe(path_for(expected["js_log"]["path"]).read_text(), budget, "JS")
                if (expected.get("all_pass") != "js-actors: ALL PASS"
                        or baseline["labels"] != expected["labels"] or baseline["traces"] != expected["traces"]):
                    raise RuntimeError("actor oracle projection differs from its retained JS witness")

        def cached_phase(label, argv, directory, proof, request, outputs):
            if proof.is_file():
                previous = json.loads(proof.read_text())
                if (previous.get("request") == request and all(
                        p.is_file() and digest(p) == previous.get("outputs", {}).get(p.name) for p in outputs)):
                    return True
            proof.unlink(missing_ok=True)
            run(label, argv, cwd=directory)
            save(proof, {"request": request, "outputs": {p.name: digest(p) for p in outputs}})
            return False

        def compile_native(name):
            source = out / (name + ".scm")
            folder, manifest = split_source(source, host_unit=host_unit, host_scheme=out / "host.scm",
                                            gsi=gsi, splitter=splitter, out=out, run=run)
            build = {"stage": name, "source_sha256": digest(source), "split_manifest": str(folder / "manifest.json"),
                     "split_manifest_sha256": digest(folder / "manifest.json"), "units": [],
                     "host_optimization": args.host_optimization,
                     "standard_bindings": args.standard_bindings, "scheme_compiler_flags": gsc_flags,
                     "link_metadata_c_flags": flags, "native_link_flags": link_flags}
            builds.append(build)
            if (manifest["units"][0].get("file") != "host.scm"
                    or manifest["units"][0].get("indivisible_ffi_host") is not True):
                raise RuntimeError("ordinal zero must be the frozen indivisible FFI host")
            c_units, objects, stems = [], [], set()
            for ordinal, row in enumerate(manifest["units"]):
                # This request intentionally excludes the runtime option:
                # Scheme -> C is identical at host -O0 and host -O1.
                request = unit_cache_request(row, ordinal, tool_identity)
                directory = out / "native-unit-cache" / key(request)
                directory.mkdir(parents=True, exist_ok=True)
                stem = f"unit_{key(request)[:16]}"
                if stem in stems:
                    raise RuntimeError("two units share one content key: " + row["file"])
                stems.add(stem)
                scheme, cfile = (directory / (stem + suffix) for suffix in (".scm", ".c"))
                optimization = args.host_optimization if ordinal == 0 else 0
                object_flags = ["-O" + str(optimization), *flags[1:]]
                obj = directory / (stem + ".O" + str(optimization) + ".o")
                if ordinal == 0 and args.host_no_inline_functions:
                    object_flags.append("-fno-inline-functions")
                    obj = directory / (stem + ".O1.noinline.o")
                    optimization = "1.noinline"
                raw = (folder / row["file"]).read_bytes()
                if not scheme.is_file() or scheme.read_bytes() != raw:
                    scheme.write_bytes(raw)
                reused_c = cached_phase(name + f"-unit-{ordinal:04d}-scheme-to-c",
                    [gsc, "-c", *gsc_flags, "-o", cfile, scheme], directory, directory / "scheme-c.json", request, [cfile])
                object_request = {"request": request, "c_sha256": digest(cfile), "flags": object_flags}
                reused_o = cached_phase(name + f"-unit-{ordinal:04d}-object",
                    [clang, *object_flags, "-c", cfile, "-o", obj], directory,
                    directory / ("object-O" + str(optimization) + ".json"), object_request, [obj])
                c_units.append(cfile)
                objects.append(obj)
                build["units"].append({"ordinal": ordinal, **row, "c": str(cfile), "c_sha256": digest(cfile),
                                       "object": str(obj), "object_sha256": digest(obj),
                                       "c_flags": object_flags,
                                       "scheme_compiler_flags": gsc_flags,
                                       "reused_c": reused_c, "reused_object": reused_o})
                progress()
                print(name, f"UNIT {ordinal + 1}/{len(manifest['units'])}", "REUSED" if reused_c and reused_o else "BUILT", flush=True)
            # Gambit's link translation consumes C metadata, independently of
            # which optimization built each object. Reuse it across the option.
            link_request = {"tools": tool_identity, "units": [
                {"c": str(c), "c_sha256": digest(c)} for c in c_units]}
            directory = out / "native-link-cache" / key(link_request)
            directory.mkdir(parents=True, exist_ok=True)
            link_c, link_o = directory / "program_.c", directory / "program_.o"
            cached_phase(name + "-link-unit", [gsc, "-link", "-o", link_c, *c_units], directory,
                         directory / "link-c.json", link_request, [link_c])
            object_request = {"link": link_request, "c_sha256": digest(link_c), "flags": flags}
            cached_phase(name + "-link-object", [clang, *flags, "-c", link_c, "-o", link_o], directory,
                         directory / "link-object.json", object_request, [link_o])
            executable_request = {"link": link_request, "link_object_sha256": digest(link_o),
                "objects": [{"path": str(o), "sha256": digest(o), "flags": unit["c_flags"]}
                            for o, unit in zip(objects, build["units"])], "link_flags": link_flags}
            image_directory = directory / "images" / key(executable_request)
            image_directory.mkdir(parents=True, exist_ok=True)
            executable = image_directory / "program"
            cached_phase(name + "-native-link", [clang, *objects, link_o, *link_flags, "-o", executable], directory,
                         image_directory / "native-link.json", executable_request, [executable])
            destination = out / name
            shutil.copy2(executable, destination)
            build["executable_sha256"] = digest(destination)
            build["executable"] = str(destination)
            build["link_order"] = [str(p) for p in c_units]
            progress()
            return destination

        def actor_image(name, diagnostic_prefix=None):
            original = (out / (name + ".scm")).read_bytes()
            if not original.endswith(ENTRY):
                raise RuntimeError("compiler source lacks its exact final native-main entry")
            stem = name + ("-actors-diagnostic" if diagnostic_prefix else "-actors")
            overlay = out / (stem + ".scm")
            prefix = diagnostic_prefix.read_bytes() + b"\n" if diagnostic_prefix else b""
            overlay.write_bytes(original[:-len(ENTRY)] + b"\n" + prefix + args.actor_body.read_bytes())
            if not overlay.read_bytes().endswith(args.actor_body.read_bytes()):
                raise RuntimeError("diagnostic overlay changed the original actor body suffix")
            bind(overlay)
            executable = compile_native(stem)
            return executable, overlay

        def actor_gate(name):
            executable, _ = actor_image(name)
            results = {}
            for budget in BUDGETS:
                env = os.environ.copy()
                env["NATIVE_ACTOR_BUDGET"] = budget
                env.pop("BL_NATIVE_C_GC_INTERVAL", None)
                output = run(name + "-actors-" + budget, [executable], cwd=root, env=env)
                result = observe(output, budget, "NATIVE")
                expected = oracle["budgets"][budget]
                if result["labels"] != expected["labels"] or result["traces"] != expected["traces"]:
                    raise RuntimeError(name + " actor checks/traces differ from original JavaScript at " + budget)
                results[budget] = result
                unchanged()
            actor_results[name] = results
            return results

        def admit_stage1(receipt_path):
            nonlocal resumed_stage1
            bind(receipt_path)
            checkpoint = json.loads(receipt_path.read_text())
            if (checkpoint.get("schema") != "bl.native.bounded-build" or checkpoint.get("version") != 1
                    or checkpoint.get("status") not in ("stage1-compiled-not-qualified", "stage1-actors-compiled-not-qualified", "failed")
                    or checkpoint.get("compile_deadline_seconds") != COMPILE_DEADLINE
                    or checkpoint.get("driver_sha256") != digest(base / "fixpoint.py")):
                raise RuntimeError("stage1 resume lacks the exact original bounded checkpoint")
            for name, expected in checkpoint["inputs"].items():
                bind(path_for(name), expected)
            selected = [b for b in checkpoint["builds"] if b.get("stage") == "stage1"]
            if len(selected) != 1:
                raise RuntimeError("stage1 resume requires exactly one complete native compiler")
            selected = selected[0]
            if (selected["source_sha256"] != digest(out / "stage1.scm")
                    or selected["scheme_compiler_flags"] != gsc_flags
                    or selected["host_optimization"] != args.host_optimization
                    or selected["native_link_flags"] != link_flags
                    or selected["link_metadata_c_flags"] != flags
                    or checkpoint["compiler_recipe"]["sha256"] != compiler_recipe["sha256"]
                    or selected["link_order"] != [u["c"] for u in selected["units"]]):
                raise RuntimeError("stage1 resume changed Source, compiler, flags or link order")
            for ordinal, unit in enumerate(selected["units"]):
                expected_flags = ["-O" + str(args.host_optimization if ordinal == 0 else 0), *flags[1:]]
                if ordinal == 0 and args.host_no_inline_functions:
                    expected_flags.append("-fno-inline-functions")
                if (unit["ordinal"] != ordinal or unit["c_flags"] != expected_flags
                        or unit["scheme_compiler_flags"] != gsc_flags):
                    raise RuntimeError("stage1 resume changed a unit ordinal or exact ABI recipe")
                bind(path_for(unit["c"]), unit["c_sha256"])
                bind(path_for(unit["object"]), unit["object_sha256"])
                bind(path_for(unit["c"]).with_suffix(".scm"), unit["sha256"])
            bind(path_for(selected["split_manifest"]), selected["split_manifest_sha256"])
            image = path_for(selected["executable"]).resolve()
            if image != out / "stage1":
                raise RuntimeError("stage1 resume selects another compiler directory")
            bind(image, selected["executable_sha256"])
            if image.read_bytes()[:4] != b"\x7fELF" or not os.access(image, os.X_OK):
                raise RuntimeError("stage1 resume is not an executable ELF")
            resumed_stage1 = {"receipt": {"path": str(receipt_path), "sha256": digest(receipt_path)},
                "image": {"path": str(image), "sha256": digest(image)}, "all_unit_artifacts_rehashed": True}
            builds.append({**selected, "admitted_existing_stage1": True})
            return image

        def check_emitted(source):
            raw = source.read_bytes()
            if (not raw.startswith(host_unit) or not raw.endswith(ENTRY)
                    or len(raw) <= len(host_unit) + len(ENTRY)):
                raise RuntimeError("native emitted Source changed frozen host or native-main entry")

        def archive_output(path):
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise RuntimeError("generated stage path is not an owned regular file")
            if path.exists():
                destination = attempts / ("previous-" + path.name)
                path.replace(destination)

        def admit_self_emission(receipt_path, image):
            bind(receipt_path)
            witness = json.loads(receipt_path.read_text())
            if (witness.get("schema") != "bl.native.self-emission-check" or witness.get("version") != 1
                    or witness.get("status") != "pass" or witness.get("self_emission_succeeded") is not True
                    or witness.get("deadline_seconds") != 240 or witness.get("timeout") is not False
                    or witness.get("exit") != 0 or witness.get("sdk_launched") is not False
                    or witness.get("checker_interprets_source_or_anf") is not False
                    or witness.get("candidate_was_fresh") is not True
                    or witness.get("frozen_host_prefix_equal") is not True
                    or witness.get("native_main_entry_equal") is not True
                    or witness.get("marker") != "NATIVE_SELF_COMPILE 34 namespaces"
                    or witness.get("cleanup", {}).get("errors") != []
                    or not 0 < witness.get("child_seconds", 1000000) <= 240
                    or witness.get("derived_native_image") is not None):
                raise RuntimeError("self-emission resume lacks an actual successful exact native witness")
            for name, expected in witness["inputs"].items():
                bind(path_for(name), expected)
            checker = (base / "check-self-emission.py").resolve()
            required = (checker, args.stage1_receipt.resolve(), image, out / "bundle.scm", out / "host.scm",
                        out / "stage1.scm", out / "prelude.scm", base / "sdk-pin.json")
            if any(witness["inputs"].get(str(p)) != digest(p) for p in required):
                raise RuntimeError("self-emission resume omits an exact checker/image/bundle/host/pin input")
            candidate = path_for(witness["candidate"]["path"]).resolve()
            if witness["candidate"].get("accepted") is not True or witness["argv"] != [
                    str(image), "--compile", str(out / "bundle.scm"), str(out / "host.scm"), str(candidate)]:
                raise RuntimeError("self-emission resume selects another actual invocation")
            bind(candidate, witness["candidate"]["sha256"])
            log = path_for(witness["log_path"])
            bind(log, witness["log_sha256"])
            output = log.read_text(errors="replace")
            if output != witness["stdout"] or [l for l in output.splitlines() if l.startswith("NATIVE_SELF_COMPILE ")] != ["NATIVE_SELF_COMPILE 34 namespaces"]:
                raise RuntimeError("self-emission resume log differs from its exact eighteen-namespace witness")
            check_emitted(candidate)
            destination = out / "stage2.scm"
            if destination.resolve() == candidate:
                raise RuntimeError("resumed candidate must remain separately preserved")
            archive_output(destination)
            shutil.copy2(candidate, destination)
            bind(destination, witness["candidate"]["sha256"])
            self_emissions.append({"stage": "stage1", "resumed_actual_witness": True,
                "receipt": {"path": str(receipt_path), "sha256": digest(receipt_path)},
                "image_sha256": digest(image), "log_sha256": digest(log),
                "source_sha256": digest(destination), "seconds": witness["child_seconds"]})
            return destination

        def emit_source(name, image, next_name):
            destination = out / (next_name + ".scm")
            archive_output(destination)
            env = os.environ.copy()
            env["BL_NATIVE_TRACE"] = "0"
            output = run(name + "-builds-" + next_name,
                [image, "--compile", out / "bundle.scm", out / "host.scm", destination],
                cwd=root, timeout=args.timeout, env=env)
            if (not destination.is_file() or destination.is_symlink()
                    or [l for l in output.splitlines() if l.startswith("NATIVE_SELF_COMPILE ")] != ["NATIVE_SELF_COMPILE 34 namespaces"]):
                raise RuntimeError(name + " did not emit a fresh exact original18 Source compilation")
            check_emitted(destination)
            bind(destination)
            self_emissions.append({"stage": name, "resumed_actual_witness": False,
                "image_sha256": digest(image), "source_sha256": digest(destination),
                "log_sha256": runs[-1]["log_sha256"], "seconds": runs[-1]["seconds"]})
            return destination

        def source_gate(name, image):
            output = run(name + "-source-corpus",
                [image, "--eval", out / "bundle.scm", args.corpus.resolve()], cwd=root, timeout=COMPILE_DEADLINE)
            if output.splitlines().count("NATIVE_COMPILER_SOURCE_CORPUS_OK") != 1 or any(
                    line.startswith("FAIL ") for line in output.splitlines()):
                raise RuntimeError(name + " lacks its actual original Source compilation/execution witness")
            source_results[name] = {"image_sha256": digest(image), "corpus_sha256": digest(args.corpus),
                "output_sha256": hashlib.sha256(output.encode()).hexdigest(), "log_sha256": runs[-1]["log_sha256"]}
            return output

        if args.stage1_receipt:
            stage1 = admit_stage1(args.stage1_receipt.resolve())
        else:
            stage1 = compile_native("stage1")
        unchanged()
        if args.compile_stage1_actors_only:
            image, overlay = actor_image("stage1", args.actor_diagnostic_prefix)
            unchanged()
            receipt = {"schema": ("bl.native.stage1-actor-diagnostic-build" if args.actor_diagnostic_prefix else "bl.native.stage1-actor-build"), "version": 1,
                       "status": ("diagnostic-compiled-not-qualified" if args.actor_diagnostic_prefix else "compiled-not-qualified"), "executed": False,
                       "diagnostic_prefix": ({"path": str(args.actor_diagnostic_prefix), "sha256": digest(args.actor_diagnostic_prefix)}
                                             if args.actor_diagnostic_prefix else None),
                       "original_body_unchanged_suffix": True,
                       "original_qualifier_admission": False, "full_driver_only": True,
                       "sdk-pin": pin, "actor_capture": actor_capture,
                       "core": {"path": str(out / "stage1.scm"), "sha256": digest(out / "stage1.scm"),
                                "prefix_sha256": hashlib.sha256((out / "stage1.scm").read_bytes()[:-len(ENTRY)]).hexdigest(),
                                "entry": ENTRY.decode()},
                       "body": {"path": str(args.actor_body), "sha256": digest(args.actor_body)},
                       "source": {"path": str(overlay), "sha256": digest(overlay)},
                       "image": {"path": str(image), "sha256": digest(image)},
                       "compile_deadline_seconds": COMPILE_DEADLINE,
                       "host_optimization": args.host_optimization,
                            "host_no_inline_functions": args.host_no_inline_functions,
                       "standard_bindings": args.standard_bindings, "scheme_compiler_flags": gsc_flags,
                       "inputs": dict(inputs), "driver_sha256": digest(here), "compiler_recipe": compiler_recipe,
                       "builds": builds, "runs": runs}
            save(out / ("stage1-actors-diagnostic-build.json" if args.actor_diagnostic_prefix else "stage1-actors-build.json"), receipt)
            progress("stage1-actors-diagnostic-compiled-not-qualified" if args.actor_diagnostic_prefix else "stage1-actors-compiled-not-qualified")
            print("NATIVE_STAGE1_ACTOR_DIAGNOSTIC_READY" if args.actor_diagnostic_prefix else "NATIVE_STAGE1_ACTOR_IMAGE_READY", digest(image), flush=True)
            return
        if args.compile_stage1_only:
            progress("stage1-compiled-not-qualified")
            print("NATIVE_STAGE1_IMAGE_READY", digest(stage1), flush=True)
            return
        corpus1 = source_gate("stage1", stage1)
        if args.self_emission_receipt:
            stage2_source = admit_self_emission(args.self_emission_receipt.resolve(), stage1)
        else:
            stage2_source = emit_source("stage1", stage1, "stage2")
        stage2 = compile_native("stage2")
        corpus2 = source_gate("stage2", stage2)
        if corpus1 != corpus2:
            raise RuntimeError("stage1 and stage2 original Source semantics differ")
        stage3_source = emit_source("stage2", stage2, "stage3")
        h2, h3 = digest(stage2_source), digest(stage3_source)
        if h2 != h3 or stage2_source.read_bytes() != stage3_source.read_bytes():
            raise RuntimeError("native bootstrap did not reach exact stage2/stage3 Scheme byte equality")
        # Equality is witnessed BEFORE stage3 is built or executed.
        unchanged()
        stage3 = compile_native("stage3")
        corpus3 = source_gate("stage3", stage3)
        if corpus3 != corpus2:
            raise RuntimeError("stage3 actual ELF Source semantics differ")
        for name in ("stage1", "stage2", "stage3"):
            actor_gate(name)
        for budget in BUDGETS:
            for name in ("stage2", "stage3"):
                if any(actor_results["stage1"][budget][field] != actor_results[name][budget][field]
                       for field in ("labels", "traces", "witness")):
                    raise RuntimeError(name + " original actor semantics differ at " + budget)
        unchanged()
        report = {"schema": "bl.native.bootstrap-fixpoint", "version": 3, "status": "qualified",
                  "stage0": "canonical BL closure on the pinned SDK; no SDK launched by this driver",
                  "stage1": "actual native image of the fresh canonical Source closure",
                  "stage2": "original BL Source compiled by actual native stage1",
                  "stage3": "original BL Source compiled by actual native stage2",
                  "stage2-sha256": h2, "stage3-sha256": h3, "stage2-stage3-byte-equal": True,
                  "stage3-built-and-executed": True,
                  "stage1-stage2-stage3-source-corpus-equal": True,
                  "stage1-stage2-stage3-original-actor-corpus-equal": True,
                  "each-stage-own-core-and-original-body": True,
                  "all-actor-budgets": list(BUDGETS), "actor_capture": actor_capture,
                  "self_emissions": self_emissions, "resumed_stage1": resumed_stage1,
                  "host_optimization": args.host_optimization,
                  "host_no_inline_functions": args.host_no_inline_functions,
                  "standard_bindings": args.standard_bindings, "scheme_compiler_flags": gsc_flags,
                  "actor_oracle_sha256": digest(args.actor_oracle), "actor_results": actor_results,
                  "source_results": source_results,
                  "inputs": inputs, "driver_sha256": digest(here), "compiler_recipe": compiler_recipe,
                  "builds": builds, "runs": runs}
        save(evidence, report)
        save(attempts / "full-fixpoint.json", report)
        progress("qualified")
        print("NATIVE_FULL_BOOTSTRAP_FIXPOINT", h2, flush=True)
    except BaseException as error:
        progress("failed", str(error))
        raise
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        lock.close()


def observe(text, budget, prefix):
    lines = text.splitlines()
    if lines.count("js-actors: ALL PASS") != 1 or any(line.startswith("FAIL ") for line in lines):
        raise RuntimeError("actor executable did not pass the original complete source")
    labels = [line[5:] for line in lines if line.startswith("PASS ")]
    if len(labels) < 461 or len(set(labels)) != len(labels):
        raise RuntimeError("original actor acceptance checks omitted or duplicated")
    traces = [line for line in lines if line.startswith(("EXIT-PARITY ", "SUP-PARITY ", "SUP-TRACE "))]
    if tuple(sum(line.startswith(p) for line in traces) for p in ("EXIT-PARITY ", "SUP-PARITY ", "SUP-TRACE ")) != (11, 10, 2):
        raise RuntimeError("original actor lifecycle/supervision trace omitted")
    marker = prefix + "_CORPUS_WITNESS "
    witnesses = [json.loads(line[len(marker):]) for line in lines if line.startswith(marker)]
    if len(witnesses) != 1 or not lines[-1].startswith(marker):
        raise RuntimeError("actor executable lacks its unique final boundary witness")
    witness = witnesses[0]
    if witness.get("budget") != budget or witness.get("cleanup") != ZERO:
        raise RuntimeError("actor budget/cleanup differs")
    if prefix == "NATIVE":
        validate_native_clock(witness)
    if any(not isinstance(witness.get(k), int) or witness[k] <= 0
           for k in ("samples", "deaths", "max_procs", "max_monitors", "max_tables", "max_links")):
        raise RuntimeError("actor execution lacks actual lifecycle observations")
    return {"labels": labels, "traces": traces, "witness": witness}


if __name__ == "__main__":
    main()
