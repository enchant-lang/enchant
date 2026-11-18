#!/usr/bin/env python3
"""Time the existing native attribution fixture on retained images. Writes no build state."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile

ATTRIB = Path(__file__).resolve().parent
NATIVE = ATTRIB.parents[1]
ROOT = NATIVE.parents[1]
PHASES = ("read", "compile", "emit")
SIZES = (32, 64, 128, 256)
FAMILIES = ("reader", "deep-fn", "wide-fn")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fixtures(work):
    yield "reader", 104, ROOT / "priv/boot/reader.bl"
    for size in SIZES:
        nested = "(fn [v] " * size + "v" + ")" * size
        wide = "[" + " ".join(["(fn [v] v)"] * size) + "]"
        for family, body in (("deep-fn", nested), ("wide-fn", wide)):
            path = work / f"{family}-{size}.bl"
            path.write_text(f"(ns reader)\n(def probe {body})\n", encoding="utf-8")
            yield family, size, path


def measure(build, source, work, repeats):
    template = (ATTRIB / "native-attrib.scm.in").read_text()
    substitutions = {
        "SOURCE": json.dumps(str(source)),
        "BUNDLE": json.dumps(str(build / "eval-bundle.scm")),
        "TARGETS": '""',
        "OUT": json.dumps(str(work)),
        "REPS": str(repeats),
        "COUNTS": "#f",
        "TIMINGS": "#t",
        "INTERVAL": "0.01",
    }
    payload = work / "observe.scm"
    payload.write_text(re.sub(r"@([A-Z]+)@", lambda m: substitutions[m[1]], template))
    meter = work / "process.txt"
    gnu_time = shutil.which("time")
    timeout = shutil.which("timeout")
    if gnu_time is None or timeout is None:
        raise SystemExit("GNU time and timeout must be on PATH.")
    result = subprocess.run(
        [gnu_time, "-f", "%U %S %M", "-o", meter, timeout, "-k", "2s", "40s",
         build / "stage1", "--eval", payload, "unused"],
        cwd=ROOT,
        env=dict(os.environ, BL_NATIVE_TRACE="0", LC_ALL="C"),
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Native probe exited {result.returncode}: {result.stdout} {result.stderr}")
    samples = [
        [float(value) * 1000 for value in line.split()[1:]]
        for line in result.stdout.splitlines() if line.startswith("A3_TIMING ")
    ]
    if len(samples) != repeats or "A3_DONE" not in result.stdout:
        raise RuntimeError(result.stdout)
    user_s, system_s, max_rss_kib = map(float, meter.read_text().split())
    return {
        "source_bytes": source.stat().st_size,
        "source_sha256": sha(source),
        "emitted_sha256": sha(work / "native.scm"),
        "emitted_bytes": (work / "native.scm").stat().st_size,
        "raw_ms": [dict(zip(PHASES, row, strict=True)) for row in samples],
        "median_ms": dict(zip(PHASES, map(statistics.median, zip(*samples)), strict=True)),
        "whole_process": {"user_s": user_s, "system_s": system_s, "max_rss_kib": int(max_rss_kib)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=NATIVE / "out/native-prepared-eval-build")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--repeats", type=int, choices=range(3, 16), default=7, metavar="3–15")
    parser.add_argument("--family", choices=FAMILIES)
    parser.add_argument("--size", type=int, choices=SIZES)
    args = parser.parse_args()
    if args.family == "reader" and args.size:
        parser.error("--size selects only generated fixtures")
    builds = [args.build.resolve()]
    if args.candidate:
        builds.append(args.candidate.resolve())
    reports = []
    fixture_index = 0
    previous = {}
    with tempfile.TemporaryDirectory(prefix="enchant-perf-probe-") as temporary:
        work = Path(temporary)
        for family, size, source in fixtures(work):
            if args.family and family != args.family:
                continue
            if args.size and (family == "reader" or size != args.size):
                continue
            paired = {}
            order = list(enumerate(builds))
            for slot, build in order if fixture_index % 2 == 0 else reversed(order):
                row = measure(build, source, work, args.repeats)
                medians = row["median_ms"]
                series = (family, slot)
                if series in previous:
                    row["doubling_exponent"] = {
                        phase: math.log2(medians[phase] / previous[series][phase])
                        for phase in PHASES
                    }
                previous[series] = medians
                paired[slot] = row
            report = {"family": family, "size": size, "baseline": paired[0]}
            if args.candidate:
                report["candidate"] = paired[1]
                report["emitted_bytes_match"] = paired[0]["emitted_sha256"] == paired[1]["emitted_sha256"]
            reports.append(report)
            fixture_index += 1
    print(json.dumps({
        "schema": "bl.native.phase-probe",
        "version": 1,
        "observer_sha256": sha(ATTRIB / "native-attrib.scm.in"),
        "images": [{"stage1_sha256": sha(b / "stage1"),
                    "eval_bundle_sha256": sha(b / "eval-bundle.scm")} for b in builds],
        "method": "One process per image and fixture. Phase timings follow setup. CPU and RSS include setup.",
        "fixtures": reports,
    }, indent=2))
    return 1 if args.candidate and any(not row["emitted_bytes_match"] for row in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
