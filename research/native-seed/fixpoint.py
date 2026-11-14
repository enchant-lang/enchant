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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--actor-body", type=Path)
    parser.add_argument("--actor-oracle", type=Path)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--host-optimization", type=int, choices=(0, 1), default=0,
                        help="Clang optimization level for the indivisible ordinal-zero host only")
    parser.add_argument("--standard-bindings", action="store_true",
                        help="assert immutable stock Gambit primitive bindings during Scheme -> C only")
    parser.add_argument("--compile-stage1-only", action="store_true",
                        help="checkpoint the real native stage1 image; never qualify a fixpoint")
    args = parser.parse_args()
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
    if not args.compile_stage1_only and (not args.actor_body or not args.actor_oracle):
        raise RuntimeError("full fixpoint requires --actor-body and --actor-oracle")
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    evidence = out / "fixpoint.json"
    evidence.unlink(missing_ok=True)
    progress_path = out / "native-build.json"
    here = Path(__file__).resolve()
    splitter = here.with_name("split-top-level.scm")
    base = root / "research/native-seed"
    inputs: dict[str, str] = {}
    runs, builds = [], []

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
        save(progress_path, {"schema": "bl.native.bounded-build", "version": 1,
                            "status": status, "error": error, "inputs": inputs,
                            "unit_target_bytes": TARGET, "unit_hard_bytes": HARD,
                            "compile_deadline_seconds": COMPILE_DEADLINE,
                            "host_optimization": args.host_optimization,
                            "standard_bindings": args.standard_bindings,
                            "scheme_compiler_flags": gsc_flags,
                            "builds": builds, "runs": runs})

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
        tool_identity = {"driver": digest(here), "splitter": digest(splitter), "flags": flags,
                         "scheme_compiler_flags": gsc_flags,
                         "link_flags": link_flags, "toolchain": tools,
                         "compiler_environment_sha256": key({name: value for name, value in os.environ.items()
                             if name.startswith(("NIX_", "GAMBIT")) or name in
                             ("PATH", "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH", "SDKROOT")}),
                         "tools": {str(p): digest(p) for p in (gsc, gsi, clang,
                                      gambit / "gambit/include/gambit.h", gambit / "gambit/lib/libgambit.so")}}
        actor_results = {}
        oracle = None
        if not args.compile_stage1_only:
            bind(args.actor_body)
            bind(args.actor_oracle)
            oracle = json.loads(args.actor_oracle.read_text())
            if (oracle.get("schema") != "bl.native.original-actor-oracle" or oracle.get("version") != 1
                    or oracle.get("status") != "complete" or oracle.get("sdk-pin") != pin
                    or oracle["application"] != {"path": "research/js-actors/test.bl", "sha256": ORIGINAL}
                    or set(oracle["budgets"]) != set(BUDGETS)):
                raise RuntimeError("actor oracle is not the complete freshly rebuilt original-source baseline")
            if path_for(oracle["body"]["path"]).resolve() != args.actor_body.resolve():
                raise RuntimeError("actor body path differs from oracle")
            for record in (oracle["application"], oracle["runtime"], oracle["body"]):
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

        def split_source(source: Path):
            body = source.read_bytes()
            if not body.startswith(host_unit):
                raise RuntimeError("native stage does not begin with the exact frozen host source")
            request = {"source_sha256": digest(source), "host_sha256": digest(out / "host.scm"),
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
            folder, manifest = split_source(source)
            build = {"stage": name, "source_sha256": digest(source), "split_manifest": str(folder / "manifest.json"),
                     "split_manifest_sha256": digest(folder / "manifest.json"), "units": [],
                     "host_optimization": args.host_optimization,
                     "standard_bindings": args.standard_bindings, "scheme_compiler_flags": gsc_flags,
                     "link_metadata_c_flags": flags, "native_link_flags": link_flags}
            builds.append(build)
            if (manifest["units"][0].get("file") != "host.scm"
                    or manifest["units"][0].get("indivisible_ffi_host") is not True):
                raise RuntimeError("ordinal zero must be the frozen indivisible FFI host")
            c_units, objects = [], []
            for ordinal, row in enumerate(manifest["units"]):
                # This request intentionally excludes the runtime option:
                # Scheme -> C is identical at host -O0 and host -O1.
                request = {"source_sha256": row["sha256"], "ordinal": ordinal, "tools": tool_identity}
                directory = out / "native-unit-cache" / key(request)
                directory.mkdir(parents=True, exist_ok=True)
                stem = f"unit_{ordinal:04d}_{key(request)[:16]}"
                scheme, cfile = (directory / (stem + suffix) for suffix in (".scm", ".c"))
                optimization = args.host_optimization if ordinal == 0 else 0
                object_flags = ["-O" + str(optimization), *flags[1:]]
                obj = directory / (stem + ".O" + str(optimization) + ".o")
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
            build["link_order"] = [str(p) for p in c_units]
            progress()
            return destination

        def actor_gate(name):
            original = (out / (name + ".scm")).read_bytes()
            if not original.endswith(ENTRY):
                raise RuntimeError("compiler source lacks its exact final native-main entry")
            overlay = out / (name + "-actors.scm")
            overlay.write_bytes(original[:-len(ENTRY)] + b"\n" + args.actor_body.read_bytes())
            bind(overlay)
            executable = compile_native(name + "-actors")
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

        stage1 = compile_native("stage1")
        unchanged()
        if args.compile_stage1_only:
            progress("stage1-compiled-not-qualified")
            print("NATIVE_STAGE1_IMAGE_READY", digest(stage1), flush=True)
            return
        corpus1 = run("stage1-source-corpus", [stage1, "--eval", out / "bundle.scm", args.corpus.resolve()],
                      cwd=root, timeout=COMPILE_DEADLINE)
        if "NATIVE_COMPILER_SOURCE_CORPUS_OK" not in corpus1:
            raise RuntimeError("source corpus did not witness native compilation and execution")
        actor1 = actor_gate("stage1")
        (out / "stage2.scm").unlink(missing_ok=True)
        built2 = run("stage1-builds-stage2", [stage1, "--compile", out / "bundle.scm", out / "host.scm", out / "stage2.scm"],
                     cwd=root, timeout=args.timeout)
        if (not (out / "stage2.scm").is_file() or not any(
                line.startswith("NATIVE_SELF_COMPILE ") and line.endswith(" namespaces") for line in built2.splitlines())):
            raise RuntimeError("native stage1 did not witness a fresh original-source stage2 build")
        bind(out / "stage2.scm")
        stage2 = compile_native("stage2")
        corpus2 = run("stage2-source-corpus", [stage2, "--eval", out / "bundle.scm", args.corpus.resolve()],
                      cwd=root, timeout=COMPILE_DEADLINE)
        if corpus1 != corpus2:
            raise RuntimeError("stage1 and stage2 original source semantics differ")
        actor2 = actor_gate("stage2")
        for budget in BUDGETS:
            if any(actor1[budget][field] != actor2[budget][field] for field in ("labels", "traces", "witness")):
                raise RuntimeError("stage1 and stage2 original actor semantics differ: " + budget)
        (out / "stage3.scm").unlink(missing_ok=True)
        built3 = run("stage2-builds-stage3", [stage2, "--compile", out / "bundle.scm", out / "host.scm", out / "stage3.scm"],
                     cwd=root, timeout=args.timeout)
        if (not (out / "stage3.scm").is_file() or not any(
                line.startswith("NATIVE_SELF_COMPILE ") and line.endswith(" namespaces") for line in built3.splitlines())):
            raise RuntimeError("native stage2 did not witness a fresh original-source stage3 build")
        bind(out / "stage3.scm")
        h2, h3 = digest(out / "stage2.scm"), digest(out / "stage3.scm")
        if h2 != h3 or (out / "stage2.scm").read_bytes() != (out / "stage3.scm").read_bytes():
            raise RuntimeError("native bootstrap did not reach a stage2/stage3 Scheme artifact fixpoint")
        unchanged()
        report = {"schema": "bl.native.bootstrap-fixpoint", "version": 2, "status": "qualified",
                  "stage0": "canonical BL compiler captured once on qualified SDK",
                  "stage1": "canonical reader/compiler/emitter compiled to bounded Scheme/C units",
                  "stage2": "original BL source compiled by native stage1",
                  "stage3": "original BL source compiled by native stage2",
                  "stage2-sha256": h2, "stage3-sha256": h3, "stage2-stage3-byte-equal": True,
                  "stage1-stage2-source-corpus-equal": True, "stage1-stage2-original-actor-corpus-equal": True,
                  "host_optimization": args.host_optimization,
                  "standard_bindings": args.standard_bindings, "scheme_compiler_flags": gsc_flags,
                  "actor_oracle_sha256": digest(args.actor_oracle), "actor_results": actor_results,
                  "inputs": inputs, "builds": builds, "runs": runs}
        save(evidence, report)
        progress("qualified")
        print("NATIVE_BOOTSTRAP_FIXPOINT", h2, flush=True)
    except BaseException as error:
        progress("failed", str(error))
        raise


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
    if any(not isinstance(witness.get(k), int) or witness[k] <= 0
           for k in ("samples", "deaths", "max_procs", "max_monitors", "max_tables", "max_links")):
        raise RuntimeError("actor execution lacks actual lifecycle observations")
    return {"labels": labels, "traces": traces, "witness": witness}


if __name__ == "__main__":
    main()
