#!/usr/bin/env python3
"""Compare exact --eval outputs and attribute fresh-process startup on one image."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--prepared", action="store_true",
                        help="include the qualified prepared macro bundle")
    args = parser.parse_args()
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
    for record in records.values():
        record["median_ms"] = statistics.median(record["milliseconds"])
    args.out.write_text(json.dumps({
        "image_sha256": sha(image), "corpus_sha256": sha(CORPUS),
        "source_corpus_output_sha256": hashlib.sha256(outputs[0]).hexdigest(),
        "observer_sha256": sha(observer), "fixture": FIRST_RESULT,
        "scope": "fresh processes with warm filesystem caches",
        "variants": records,
    }, indent=2) + "\n")
    print("NATIVE_CURRENT_STARTUP_OBSERVED")


if __name__ == "__main__":
    main()
