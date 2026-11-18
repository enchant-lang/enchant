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


def compare_beam(image, prepared, fixture, pin_path):
    pin = json.loads(pin_path.read_bytes())
    sdk = Path(pin["sdk"])
    descriptor = sdk / "artifact.json"
    if sha(descriptor) != pin["descriptor_sha256"] or json.loads(descriptor.read_bytes())["source"] != pin["source"]:
        raise ValueError("The selected BEAM SDK differs from the immutable pin")
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
        "sdk_descriptor_sha256": sha(descriptor),
        "native_bundle_sha256": sha(prepared),
        "samples": counts,
        "median_elapsed_ms": {target: statistics.median(row["elapsed_ms"] for row in rows)
                              for target, rows in counts.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--prepared", action="store_true",
                        help="include the qualified prepared macro bundle")
    parser.add_argument("--beam-pin", type=Path,
                        help="also compare the prepared route with this exact BEAM SDK")
    args = parser.parse_args()
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
