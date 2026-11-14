#!/usr/bin/env python3
"""Run already prepared original actor artifacts; never launch BL or a build.

Use the integrator's sequential bounded cgroup. Full qualification requires
both targets at default/17/41; --native-only or --budget is observation only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ORIGINAL = "5f2ad8223fd9f053157b65266d3ee14e7fe8567b6196a78ed7ac955132b9a5c5"
BUDGETS = ["default", "17", "41"]
ZERO = {"procs": 0, "monitors": 0, "tables": 0, "names": 0, "table_names": 0,
        "runnable": 0, "input_sink": None, "critical": 0, "errors": 0}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main() -> int:
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / "research/native-seed/toolchain-pin.json").is_file())
    base = root / "research/native-seed"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, default=base / "out/original-actor-corpus/manifest.json")
    parser.add_argument("--javascript", type=Path, default=base / "out/original-actor-js/manifest.json")
    parser.add_argument("--evidence", type=Path, default=base / "evidence/original-actor-corpus")
    parser.add_argument("--node", type=Path)
    parser.add_argument("--budget", action="append", choices=BUDGETS)
    parser.add_argument("--native-only", action="store_true")
    parser.add_argument("--reuse-js", action="store_true", help="reuse only hash-identical retained JS witnesses")
    parser.add_argument("--run-timeout", type=int, default=120)
    args = parser.parse_args()
    budgets = list(dict.fromkeys(args.budget or BUDGETS))
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / "qualification.json"
    report_path.unlink(missing_ok=True)
    oracle_path = evidence / "oracle.json"
    oracle_path.unlink(missing_ok=True)
    report = {"schema": "bl.native.original-actor-qualification", "version": 1,
              "status": "running", "builds_launched": False, "budgets": budgets,
              "scope": "original actor corpus; Scheme host; virtual native deadlines",
              "direct_c": False, "compiler_fixpoint": False, "independent_runtime": False,
              "runs": [], "results": {}}
    inputs = {}
    artifacts = set()

    def path_for(name: str) -> Path:
        path = Path(name)
        return path if path.is_absolute() else root / path

    def bind(path: Path, expected: str | None = None) -> str:
        path = path.resolve()
        actual = digest(path)
        if expected is not None and actual != expected:
            raise RuntimeError("prepared input identity differs: " + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError("input changed during admission: " + str(path))
        inputs[str(path)] = actual
        return actual

    def identity(record: dict) -> None:
        bind(path_for(record["path"]), record["sha256"])

    def unchanged() -> None:
        for name, expected in inputs.items():
            if not Path(name).is_file() or digest(Path(name)) != expected:
                raise RuntimeError("qualification input changed: " + name)

    def save() -> None:
        report["inputs"] = inputs
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    def admit(path: Path, target: str) -> tuple[dict, set[str]]:
        old = set(inputs)
        bind(path)
        manifest = json.loads(path.read_text())
        if (manifest.get("schema") != "bl.native.original-actor-corpus" or manifest.get("version") != 1
                or manifest.get("target") != target):
            raise RuntimeError("not a prepared original " + target + " corpus manifest")
        if manifest["application"] != {"path": "research/js-actors/test.bl", "sha256": ORIGINAL}:
            raise RuntimeError("corpus source was replaced or adapted")
        if manifest.get("assertion-adaptation") != "none" or manifest.get("source-path-adaptation") != "none":
            raise RuntimeError("original assertions and source paths must be preserved")
        for record in [manifest["application"], manifest["runtime"], manifest["artifact"],
                       *manifest["inputs"], *manifest.get("assets", []),
                       *([manifest["body"]] if "body" in manifest else [])]:
            identity(record)
        return manifest, set(inputs) - old

    def observe(text: str, role: str, budget: str) -> dict:
        lines = text.splitlines()
        if "js-actors: ALL PASS" not in lines or any(line.startswith("FAIL ") for line in lines):
            raise RuntimeError(role + " did not pass the original acceptance driver")
        labels = [line[5:] for line in lines if line.startswith("PASS ")]
        if len(labels) < 461 or len(set(labels)) != len(labels):
            raise RuntimeError(role + " omitted/duplicated original acceptance checks: " + str(len(labels)))
        prefix = ("NATIVE" if role == "native" else "JS") + "_CORPUS_WITNESS "
        witnesses = [json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
        if len(witnesses) != 1 or not lines[-1].startswith(prefix):
            raise RuntimeError(role + " lacks its unique final boundary/cleanup witness")
        witness = witnesses[0]
        if witness.get("budget") != budget or witness.get("cleanup") != ZERO:
            raise RuntimeError(role + " budget or final cleanup mismatch")
        for key in ("samples", "deaths", "max_procs", "max_monitors", "max_tables", "max_links"):
            if not isinstance(witness.get(key), int) or witness[key] <= 0:
                raise RuntimeError(role + " lacks a positive " + key + " observation")
        traces = [line for line in lines if line.startswith(("EXIT-PARITY ", "SUP-PARITY ", "SUP-TRACE "))]
        if (sum(line.startswith("EXIT-PARITY ") for line in traces) != 11
                or sum(line.startswith("SUP-PARITY ") for line in traces) != 10
                or sum(line.startswith("SUP-TRACE ") for line in traces) != 2):
            raise RuntimeError(role + " omitted original lifecycle/supervision traces")
        return {"labels": labels, "traces": traces, "witness": witness}

    def run(role: str, budget: str, argv: list[str]) -> dict:
        log = evidence / (role + "-" + budget + ".log")
        log.unlink(missing_ok=True)
        started = time.monotonic()
        env = os.environ.copy()
        env["NATIVE_ACTOR_BUDGET"] = budget
        env.pop("BL_NATIVE_C_GC_INTERVAL", None)
        process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        timeout = False
        try:
            output, _ = process.communicate(timeout=args.run_timeout)
        except BaseException as error:
            timeout = isinstance(error, subprocess.TimeoutExpired)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            log.write_text(output)
            artifacts.add(log)
            report["runs"].append({"role": role, "budget": budget, "argv": argv,
                "seconds": round(time.monotonic() - started, 3), "exit": process.returncode,
                "timed_out": timeout})
            save()
            if not timeout:
                raise
        if not timeout:
            log.write_text(output)
            artifacts.add(log)
            report["runs"].append({"role": role, "budget": budget, "argv": argv,
                "seconds": round(time.monotonic() - started, 3), "exit": process.returncode,
                "timed_out": False})
        save()
        unchanged()
        if timeout or process.returncode:
            raise RuntimeError(f"{role}/{budget} {'deadline' if timeout else 'exit '+str(process.returncode)}: {output[-3000:]}")
        return observe(output, role, budget)

    try:
        if not 1 <= args.run_timeout <= 120:
            raise RuntimeError("original corpus retains its 120-second runtime deadline")
        tools_path = base / "toolchain-pin.json"
        bind(tools_path)
        bind(here)
        tools = json.loads(tools_path.read_text())
        gsi = Path(tools["gambit"]) / "bin/gsi"
        bind(gsi)
        native, native_inputs = admit(args.native.resolve(), "scheme")
        link = native["link"]
        if link.get("source-frames?") is not True or link.get("runtime-definitions") != 202:
            raise RuntimeError("native artifact lacks source frames or the complete runtime")
        for record in [link["closure-manifest"], link["prelude"], link["links"], link["host-link"], *link["host-extensions"]]:
            identity(record)
        program_bytes = path_for(native["artifact"]["path"]).read_bytes()
        prefix = path_for(link["prelude"]["path"]).read_bytes() + b"\n"
        if not program_bytes.startswith(prefix) or program_bytes[len(prefix):] != path_for(native["body"]["path"]).read_bytes():
            raise RuntimeError("original actor body is not the exact suffix after its frozen prelude")
        # Replace only the exact frozen native-text FFI suffix with its pinned
        # compiled addon. Every byte after the frozen host is unchanged BL code.
        closure_dir = path_for(link["closure-manifest"]["path"]).resolve().parent
        frozen_host_path = closure_dir / "host.scm"
        text_source_path = base / "host/native-text.scm"
        addon_path = closure_dir / "text.o1"
        addon_receipt_path = closure_dir / "text-addon.json"
        export_path = closure_dir / "chunk-export.json"
        frozen_host_sha = bind(frozen_host_path)
        text_source_sha = bind(text_source_path)
        bind(addon_receipt_path)
        bind(export_path)
        export = json.loads(export_path.read_text())
        if (export.get("schema") != "bl.native.chunk-export" or export.get("version") != 2
                or export["prelude_sha256"] != link["prelude"]["sha256"]
                or export["inputs"]["host_sha256"] != frozen_host_sha):
            raise RuntimeError("GSI transport host differs from the exact emitted prelude")
        frozen_host = frozen_host_path.read_bytes()
        text_suffix = b"\n" + text_source_path.read_bytes()
        if not frozen_host.endswith(text_suffix):
            raise RuntimeError("frozen host lacks its exact native-text FFI suffix")
        pure_host = frozen_host[:-len(text_suffix)]
        header = b";; BL native compiler. Generated from canonical BL source.\n"
        frozen_prefix = header + frozen_host + b"\n"
        if not program_bytes.startswith(frozen_prefix):
            raise RuntimeError("GSI transport cannot identify the exact frozen host boundary")
        receipt = json.loads(addon_receipt_path.read_text())
        expected_addon_key = hashlib.sha256((text_source_sha + digest(tools_path)).encode()).hexdigest()
        if receipt.get("key") != expected_addon_key:
            raise RuntimeError("compiled native-text receipt does not bind exact Source/toolchain")
        addon_sha = bind(addon_path, receipt["sha256"])
        bind(Path(tools["gambit"]) / "bin/gsc")
        library_matches = re.findall(rb'^#define BL_PCRE_PATH "([^"\n]+)"$', text_source_path.read_bytes(), re.MULTILINE)
        if len(library_matches) != 1:
            raise RuntimeError("pinned native-text runtime library declaration changed")
        bind(Path(os.fsdecode(library_matches[0])))
        compiled_bl_suffix = program_bytes[len(frozen_prefix):]
        load_addon = ("\n(load " + json.dumps(str(addon_path), ensure_ascii=False) + ")\n").encode()
        interpreted_bytes = header + pure_host + load_addon + compiled_bl_suffix
        interpreted_path = evidence / "original-actors-gsi.scm"
        interpreted_path.write_bytes(interpreted_bytes)
        bind(interpreted_path)
        if not interpreted_bytes.endswith(compiled_bl_suffix):
            raise RuntimeError("GSI transport changed emitted BL bytes")
        native_program_path = interpreted_path
        report["native_transport"] = {
            "kind": "gsi-with-exact-compiled-native-text-addon",
            "original_program": native["artifact"],
            "frozen_host": {"path": str(frozen_host_path), "sha256": frozen_host_sha},
            "pure_host_sha256": hashlib.sha256(pure_host).hexdigest(),
            "ffi_source": {"path": str(text_source_path), "sha256": text_source_sha},
            "addon": {"path": str(addon_path), "sha256": addon_sha},
            "receipt": {"path": str(addon_receipt_path), "sha256": digest(addon_receipt_path)},
            "unchanged_bl_suffix_sha256": hashlib.sha256(compiled_bl_suffix).hexdigest(),
            "unchanged_bl_suffix_bytes": len(compiled_bl_suffix),
            "executed_program": {"path": str(interpreted_path), "sha256": digest(interpreted_path)},
            "source_assertion_adaptation": "none", "builds_launched": False}
        partition = json.loads(path_for(link["closure-manifest"]["path"]).read_text())
        for record in [partition["metadata"], *partition["units"]]:
            identity(record)
        pin = link["sdk-pin"]
        descriptor = Path(pin["sdk"]) / "artifact.json"
        bind(descriptor, pin["descriptor_sha256"])
        if json.loads(descriptor.read_text())["source"] != pin["source"]:
            raise RuntimeError("qualified SDK source changed")
        source = path_for(native["application"]["path"]).read_text()
        authored = re.findall(r'^\((?:defn-?|proc/defserver|proc\.super/defsupervisor)\s+([^\s()]+)', source, re.MULTILINE)
        absent = [name for name in authored if "native.kernel/" + name not in link["emitted-bindings"]]
        if absent:
            raise RuntimeError("original source definitions omitted: " + ", ".join(absent))
        report["authored_definitions_retained"] = len(authored)
        js = None
        cache_path = evidence / "js-cache.json"
        cache = {"identity": None, "budgets": {}}
        if not args.native_only:
            js, _ = admit(args.javascript.resolve(), "javascript")
            if js["application"] != native["application"] or js["runtime"] != native["runtime"] or js["sdk-pin"] != pin:
                raise RuntimeError("targets do not share original source/runtime/SDK identities")
            node = args.node or Path(shutil.which("node") or "")
            if not node.is_file():
                raise RuntimeError("Node executable missing; pass --node /absolute/path")
            node = node.resolve()
            bind(node)
            driver = base / "corpus/js-witness.mjs"
            bind(driver)
            # Shared inputs are deliberately included: cache reuse binds every
            # JS source/asset and its exact executable/witness, not native code.
            js_names = {str(args.javascript.resolve()), str(node), str(driver.resolve()), str(descriptor.resolve())}
            for record in [js["application"], js["runtime"], js["artifact"], *js["inputs"], *js["assets"]]:
                js_names.add(str(path_for(record["path"]).resolve()))
            js_identity = hashlib.sha256(json.dumps({name: inputs[name] for name in sorted(js_names)}, sort_keys=True).encode()).hexdigest()
            if args.reuse_js and cache_path.is_file():
                cache = json.loads(cache_path.read_text())
                if cache.get("identity") != js_identity:
                    raise RuntimeError("JS witness cache identity changed; omit --reuse-js")
            else:
                cache["identity"] = js_identity
        report["sdk"] = pin
        report["clock"] = native["clock"]
        save()
        canonical = None
        oracle_budgets = {}
        for budget in budgets:
            result = run("native", budget, [str(gsi), str(native_program_path)])
            report["results"][budget] = {"native": result}
            if js is not None:
                cached = cache["budgets"].get(budget) if args.reuse_js else None
                log = evidence / ("javascript-" + budget + ".log")
                if cached:
                    if digest(log) != cached["log_sha256"]:
                        raise RuntimeError("retained JS witness log changed")
                    baseline = observe(log.read_text(), "javascript", budget)
                    artifacts.add(log)
                    report["runs"].append({"role": "javascript", "budget": budget, "reused": True, "log_sha256": digest(log)})
                else:
                    baseline = run("javascript", budget, [str(node), str(driver), str(path_for(js["artifact"]["path"])), budget])
                    cache["budgets"][budget] = {"log_sha256": digest(log)}
                    cache_path.write_text(json.dumps(cache, indent=2) + "\n")
                if result["labels"] != baseline["labels"] or result["traces"] != baseline["traces"]:
                    raise RuntimeError("original ordered checks/parity traces differ at budget " + budget)
                report["results"][budget]["javascript"] = baseline
                oracle_budgets[budget] = {"labels": baseline["labels"], "traces": baseline["traces"],
                    "js_log": {"path": str(log), "sha256": digest(log)}, "all_pass": "js-actors: ALL PASS"}
            if canonical is not None and result["labels"] != canonical:
                raise RuntimeError("original checks changed across actor budgets")
            canonical = result["labels"]
            save()
        unchanged()
        complete = js is not None and budgets == BUDGETS
        if js is not None:
            oracle_path.write_text(json.dumps({"schema": "bl.native.original-actor-oracle", "version": 1,
                "status": "complete" if complete else "partial", "application": native["application"],
                "runtime": native["runtime"], "sdk-pin": pin, "body": native["body"],
                "inputs": inputs, "budgets": oracle_budgets}, indent=2) + "\n")
            artifacts.add(oracle_path)
        report.update({"status": "pass" if complete else "observed-not-qualified",
            "original_actor_corpus_qualified": complete,
            "checks_per_budget": len(canonical or []),
            "inputs_after": {name: digest(Path(name)) for name in inputs}})
        print(("ORIGINAL_ACTOR_CORPUS_QUALIFIED" if complete else "ORIGINAL_ACTOR_CORPUS_OBSERVED") +
              f" {len(canonical or [])} original checks; budgets={','.join(budgets)}", flush=True)
        return 0
    except BaseException as error:
        report.update({"status": "fail", "error": str(error), "original_actor_corpus_qualified": False})
        print("ORIGINAL_ACTOR_CORPUS_FAILED " + str(error), file=sys.stderr, flush=True)
        return 1
    finally:
        report["inputs_after"] = {name: digest(Path(name)) if Path(name).is_file() else None for name in inputs}
        report["logs"] = {str(path): {"sha256": digest(path), "bytes": path.stat().st_size} for path in sorted(artifacts) if path.is_file()}
        save()


if __name__ == "__main__":
    raise SystemExit(main())
