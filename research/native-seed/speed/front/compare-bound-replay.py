#!/usr/bin/env python3
"""Compare full lowering and qualified receipt replay in fresh pinned VMs."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("donor", "receipt", "qualification", "macro_samples", "out"):
        parser.add_argument(name, type=Path)
    parser.add_argument("receipt_sha256")
    args = parser.parse_args()

    seed = Path(__file__).resolve().parents[2]
    root = seed.parents[1]
    partition = (args.donor / "partition.json").resolve()
    link_rows = (args.donor / "link-rows.etf").resolve()
    receipt = args.receipt.resolve()
    qualification = args.qualification.resolve()
    samples = args.macro_samples.resolve()
    expected_links = json.loads(qualification.read_text())["native-updater-check"]["installed-link-sha256"]
    expected_samples = hashlib.sha256(samples.read_bytes()).hexdigest()
    if hashlib.sha256(receipt.read_bytes()).hexdigest() != args.receipt_sha256:
        parser.error("receipt bytes differ from the expected digest")

    args.out.mkdir()
    base = [seed / "run", "run", seed / "speed/front/observe-links.bl", "--", partition, link_rows]
    records = []
    for index, mode in enumerate(("full", "replay", "replay", "full")):
        stem = (args.out / f"{index}-{mode}").resolve()
        report_path = stem.with_suffix(".json")
        if mode == "full":
            rest = ["--cached-registry", report_path, receipt, samples, "--force-lower"]
        else:
            rest = ["--bound-registry", report_path, receipt, samples, partition, qualification, args.receipt_sha256]
        with stem.with_suffix(".log").open("wb") as log:
            start = time.monotonic_ns()
            subprocess.run(base + rest, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
            elapsed = (time.monotonic_ns() - start) // 1000
        report = json.loads(report_path.read_text())
        members = report["members"]
        reused = sum(member["reused"] for member in members)
        if (
            not members
            or not all(member["exact-clean-definitions"] for member in members)
            or report["candidate-link-rows-sha256"] != expected_links
            or report["sample-report-sha256"] != expected_samples
            or bool(reused) != (mode == "replay")
        ):
            raise SystemExit(f"unexpected result from {mode}: {report_path}")
        records.append({
            "mode": mode, "process-wall-us": elapsed, "exact-definitions": len(members),
            "members-reused": reused,
            "recompile-reasons": dict(Counter(member["reason"] for member in members if not member["reused"])),
        })
    if len({record["exact-definitions"] for record in records}) != 1:
        raise SystemExit("different numbers of definitions compared across samples")
    result = {
        "schema": "bl.native.bound-replay-process-comparison",
        "version": 1,
        "receipt-sha256": args.receipt_sha256,
        "link-rows-sha256": expected_links,
        "macro-samples-sha256": expected_samples,
        "samples": records,
        "median-process-wall-us": {
            mode: statistics.median(r["process-wall-us"] for r in records if r["mode"] == mode)
            for mode in ("full", "replay")
        },
    }
    (args.out / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
