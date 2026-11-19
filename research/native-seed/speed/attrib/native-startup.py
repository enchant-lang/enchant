#!/usr/bin/env python3
"""Compare exact --eval outputs and attribute fresh-process startup on one image."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
import time

ATTRIB = Path(__file__).resolve().parent
CORPUS = ATTRIB.parent.parent / "fixtures/compiler-source.bl"
FIRST_RESULT = "(println (+ 40 2))\n"
PHASES = ("read_bundle", "decode_bundle", "install_macros", "eval_source")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eval_one(image, operand, argument):
    start = time.perf_counter_ns()
    result = subprocess.run(
        [image, "--eval", operand, argument],
        env=dict(os.environ, BL_NATIVE_TRACE="0"),
        capture_output=True, timeout=120, check=True,
    )
    return result.stdout, (time.perf_counter_ns() - start) / 1_000_000


def pinned_sdk(pin_path):
    pin = json.loads(pin_path.read_bytes())
    sdk = Path(pin["sdk"])
    descriptor = sdk / "artifact.json"
    if sha(descriptor) != pin["descriptor_sha256"] or json.loads(descriptor.read_bytes())["source"] != pin["source"]:
        raise ValueError("The selected BEAM SDK differs from the immutable pin")
    return sdk, pin["descriptor_sha256"]


def compare_beam(image, prepared, fixture, pin_path):
    sdk, descriptor_sha = pinned_sdk(pin_path)
    meter = shutil.which("time")
    timeout = shutil.which("timeout")
    if meter is None or timeout is None:
        raise RuntimeError("GNU time and timeout must be on PATH")
    commands = {
        "native": [image, "--eval", prepared, fixture],
        "beam": [sdk / "bin/bl", "--cold", "run", fixture],
    }
    counts = {target: [] for target in commands}
    usage = fixture.with_suffix(".usage")
    environment = dict(os.environ, BL_NATIVE_TRACE="0", LC_ALL="C", ERL_FLAGS="+S 2:2 +SDcpu 1:1 +SDio 1")
    for target in ("native", "beam", "beam", "native") * 3:
        start = time.perf_counter_ns()
        result = subprocess.run(
            [meter, "-f", "%U %S %M", "-o", usage, timeout, "-k", "2s", "25s", *commands[target]],
            env=environment, capture_output=True, check=True,
        )
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        expected = b"42\n:ok" if target == "beam" else b"42"
        assert result.stdout.strip() == expected, result.stdout
        user_s, system_s, rss_kib = map(float, usage.read_text().split())
        counts[target].append({"elapsed_ms": elapsed_ms, "cpu_s": user_s + system_s, "max_rss_kib": int(rss_kib)})
    return {
        "scope": "Fresh process through exact result and exit. Warm filesystem caches.",
        "sdk_descriptor_sha256": descriptor_sha,
        "native_bundle_sha256": sha(prepared),
        "samples": counts,
        "median_elapsed_ms": {target: statistics.median(row["elapsed_ms"] for row in rows)
                              for target, rows in counts.items()},
    }


def qualified_inputs(build, qualification):
    record = json.loads(qualification.read_bytes())
    replay = record["unchanged_release_replay"]["identical_artifacts"]
    for name, identity in record["images"].items():
        if sha(build / name) != identity:
            raise ValueError(f"{name} differs from its qualified image")
    bundles = ("bundle.scm", "eval-bundle.scm", "eval-prepared.scm")
    for name in bundles:
        if sha(build / name) != replay[name]:
            raise ValueError(f"{name} differs from its qualified bundle")
    if (sha(CORPUS) != record["source_corpus_sha256"]
            or replay["eval-prepared.scm"] != record["prepared_macro_bundle_sha256"]):
        raise ValueError("Source or prepared macro identity differs from qualification")
    receipt = build / Path(record["receipt"]["path"]).name
    if sha(receipt) != record["receipt"]["sha256"]:
        raise ValueError("Native fixpoint receipt differs from qualification")
    fixpoint = json.loads(receipt.read_bytes())
    required = ("stage2-stage3-byte-equal", "stage3-built-and-executed",
                "stage1-stage2-stage3-source-corpus-equal",
                "stage1-stage2-stage3-original-actor-corpus-equal",
                "each-stage-own-core-and-original-body")
    if (fixpoint["status"] != "qualified" or not all(fixpoint.get(k) is True for k in required)
            or set(fixpoint["all-actor-budgets"]) != {"default", "17", "41"}):
        raise ValueError("Incomplete native Source, actor, or fixpoint qualification")
    return record, bundles


def benchmark_source(source, commands, order, workspace, environment, meter, timeout,
                     expected=None, allow_beam_refusal=False):
    fixture = workspace / source.name
    shutil.copyfile(source, fixture)
    source_sha = sha(fixture)
    samples = {mode: [] for mode in commands}
    refused = {}
    attempted = []
    usage = workspace / "usage"
    for mode in order:
        if mode in refused:
            continue
        attempted.append(mode)
        start = time.perf_counter_ns()
        result = subprocess.run([meter, "-f", "%U %S %M", "-o", usage,
                                 timeout, "-k", "2s", "60s", *commands[mode], fixture],
                                cwd=workspace, env=environment, capture_output=True)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        if result.returncode:
            if mode == "beam" and allow_beam_refusal and 0 < result.returncode < 124:
                refused[mode] = {"exit": result.returncode,
                                 "diagnostic": result.stderr.decode(errors="replace").splitlines()[:2]}
                continue
            raise RuntimeError(f"{mode} exited {result.returncode}: {(result.stdout + result.stderr)[-4000:]!r}")
        output = result.stdout
        if mode == "beam":
            if not output.endswith(b":ok\n"):
                raise ValueError(f"BEAM CLI final value differs: {output[-160:]!r}")
            output = output.removesuffix(b":ok\n")
        identity = hashlib.sha256(output).hexdigest()
        if expected is None and output.strip():
            expected = identity
        if identity != expected:
            raise ValueError(f"{mode} output differs from the reference: {output[-1500:]!r}")
        user_s, sys_s, rss = map(float, usage.read_text().split())
        samples[mode].append({"wall_ms": elapsed, "cpu_s": user_s + sys_s, "peak_rss_kib": int(rss)})
    if sha(source) != source_sha or sha(fixture) != source_sha:
        raise ValueError("The benchmark Source changed during the comparison")
    return {"source_sha256": source_sha, "stdout_sha256": expected, "order": attempted,
            "samples": samples, "refused": refused,
            "median": {mode: {key: statistics.median(row[key] for row in rows) for key in rows[0]}
                       for mode, rows in samples.items() if rows}}


def compare_source_workflow(build, qualification, pin_path, workflow):
    record, bundles = qualified_inputs(build, qualification)
    sdk, descriptor_sha = pinned_sdk(pin_path)
    meter = shutil.which("time")
    timeout = shutil.which("timeout")
    if meter is None or timeout is None:
        raise RuntimeError("GNU time and timeout must be on PATH")
    commands = {name: [build / "stage1", "--eval", build / name] for name in bundles}
    commands["beam"] = [sdk / "bin/bl", "--cold", "run"]
    modes = tuple(commands)
    order = (modes + tuple(reversed(modes))) * 2
    with tempfile.TemporaryDirectory(prefix="native-corpus-workflow-") as directory:
        workspace = Path(directory)
        runtime = workspace / "runtime"
        runtime.mkdir(mode=0o700)
        environment = dict(os.environ, LC_ALL="C.UTF-8", BL_NATIVE_TRACE="0", XDG_RUNTIME_DIR=str(runtime),
                           ERL_FLAGS="+S 2:2 +SDcpu 1:1 +SDio 1")
        corpus = benchmark_source(CORPUS, commands, order, workspace, environment, meter, timeout,
                                  expected=record["source_result_sha256"], allow_beam_refusal=True)
        example = None
        if workflow:
            example = benchmark_source(workflow, commands, order, workspace, environment, meter, timeout)
            example["source"] = str(workflow)
        failures = {}
        malformed = workspace / "malformed.bl"
        malformed.write_text("]\n")
        for mode, command in commands.items():
            refusal = subprocess.run([timeout, "-k", "2s", "60s", *command, malformed],
                                     cwd=workspace, env=environment, capture_output=True)
            if refusal.returncode <= 0 or refusal.returncode >= 124 or not (refusal.stdout or refusal.stderr):
                raise ValueError(f"{mode} failed to reject malformed Source: {refusal.returncode}")
            failures[mode] = {"exit": refusal.returncode, "stdout_bytes": len(refusal.stdout),
                              "stderr_bytes": len(refusal.stderr)}
    return {"schema": "bl.native.qualified-source-workflow.v1",
            "scope": "Fresh command through original Source and exit. BEAM prints an additional :ok CLI value.",
            "image_sha256": record["images"]["stage1"],
            "bundle_sha256": {name: sha(build / name) for name in bundles},
            "qualification_sha256": sha(qualification), "fixpoint_receipt_sha256": record["receipt"]["sha256"],
            "sdk_descriptor_sha256": descriptor_sha, "corpus": corpus, "workflow": example,
            "malformed_source": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--prepared", action="store_true",
                        help="include the qualified prepared macro bundle")
    parser.add_argument("--beam-pin", type=Path,
                        help="also compare the prepared route with this exact BEAM SDK")
    parser.add_argument("--source-qualification", type=Path,
                        help="compare the complete original Source corpus on the qualified native and BEAM products")
    parser.add_argument("--source-workflow", type=Path,
                        help="also compare a standalone Source script on all four routes")
    args = parser.parse_args()
    if args.source_workflow and not args.source_qualification:
        parser.error("--source-workflow requires --source-qualification")
    if args.source_qualification:
        if args.beam_pin is None:
            parser.error("--source-qualification requires --beam-pin")
        report = compare_source_workflow(args.build.resolve(), args.source_qualification, args.beam_pin,
                                         args.source_workflow)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print("NATIVE_QUALIFIED_SOURCE_WORKFLOW_OBSERVED")
        return
    if args.beam_pin and not args.prepared:
        parser.error("--beam-pin requires --prepared")
    build = args.build.resolve()
    image = build / "stage1"
    bundles = [build / "bundle.scm", build / "eval-bundle.scm"]
    if args.prepared:
        bundles.append(build / "eval-prepared.scm")
    observer = ATTRIB / "native-startup-phases.scm"
    outputs = [eval_one(image, bundle, CORPUS)[0] for bundle in bundles]
    assert all(output == outputs[0] for output in outputs)
    assert b"NATIVE_COMPILER_SOURCE_CORPUS_OK" in outputs[0]
    records = {bundle.name: {"sha256": sha(bundle), "bytes": bundle.stat().st_size,
                            "milliseconds": [], "phases_ms": []} for bundle in bundles}
    beam = None
    order = (*bundles, *reversed(bundles))
    with tempfile.TemporaryDirectory(prefix="native-first-result-") as directory:
        fixture = Path(directory) / "first-result.bl"
        fixture.write_text(FIRST_RESULT)
        for bundle in order * 4:
            stdout, milliseconds = eval_one(image, bundle, fixture)
            assert stdout.strip() == b"42", stdout
            records[bundle.name]["milliseconds"].append(milliseconds)
        for bundle in order * 2:
            stdout, milliseconds = eval_one(image, observer, bundle)
            phases = re.fullmatch(rb"42\s+\(STARTUP_PHASES ([^()]+)\)\s*", stdout)
            assert phases, stdout
            times = dict(zip(PHASES, map(float, phases[1].split()), strict=True))
            times["outer_process_and_observer"] = milliseconds - sum(times.values())
            records[bundle.name]["phases_ms"].append(times)
        if args.beam_pin:
            beam = compare_beam(image, build / "eval-prepared.scm", fixture, args.beam_pin)
    for record in records.values():
        record["median_ms"] = statistics.median(record["milliseconds"])
    report = {
        "image_sha256": sha(image), "corpus_sha256": sha(CORPUS),
        "source_corpus_output_sha256": hashlib.sha256(outputs[0]).hexdigest(),
        "observer_sha256": sha(observer), "fixture": FIRST_RESULT,
        "scope": "fresh processes with warm filesystem caches",
        "variants": records,
    }
    if beam is not None:
        report["beam_comparison"] = beam
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print("NATIVE_CURRENT_STARTUP_OBSERVED")


if __name__ == "__main__":
    main()
