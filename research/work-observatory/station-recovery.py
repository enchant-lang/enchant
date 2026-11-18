#!/usr/bin/env python3
"""Measure Station's actual audit recovery implementation on generated history."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from importlib.util import module_from_spec, spec_from_file_location
import hashlib
import json
from pathlib import Path
import resource
import statistics
import sys
import tempfile
import time


def load_gateway(path):
    sys.dont_write_bytecode = True
    spec = spec_from_file_location("station_gateway_replay", path)
    gateway = module_from_spec(spec)
    spec.loader.exec_module(gateway)
    return gateway


def event(index, now):
    return {"request-id": str(index), "at": now, "uid": 1000 + index % 2,
            "route": "anthropic" if index % 3 else "codex", "status": 200}


def counts(snapshot):
    assert snapshot["source"] == "audit-recovery"
    windows = snapshot["windows"]
    result = Counter({(row["uid"], row["route"]): row["requests"] for row in windows["30"]["rows"]})
    assert result == Counter({(row["uid"], row["route"]): row["requests"] for row in windows["7"]["rows"]})
    for user, scoped in snapshot["people"].items():
        uid = int(user)
        for window in scoped.values():
            assert {row["uid"] for row in window["requests"]} == {uid}
            assert sum(row["requests"] for row in window["rows"]) == sum(
                count for (owner, _), count in result.items() if owner == uid)
    return result


def measure(action, activity):
    builds = activity["audit_recoveries"]
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    result = action()
    return result, {"wall_ms": (time.perf_counter_ns() - wall) / 1e6,
                    "process_cpu_ms": (time.process_time_ns() - cpu) / 1e6,
                    "audit_recoveries": activity["audit_recoveries"] - builds}


def replay(gateway, history, viewers, audit, activity):
    now = int(time.time() * 1000)
    expected = Counter()
    with audit.open("w", encoding="utf-8") as stream:
        for index in range(history):
            row = event(index, now)
            expected[row["uid"], row["route"]] += 1
            stream.write(json.dumps(row) + "\n")
    gateway._CACHE.clear()
    gateway._RECOVERY_CACHE = None
    settings = {"gatewayAudit": str(audit), "gatewaySnapshot": str(audit.with_name("absent.json"))}

    def owner(uid):
        return {1000: "alice", 1001: "bob"}[uid]

    def snapshot():
        return gateway.snapshot(settings, owner)

    first, cold = measure(snapshot, activity)
    assert counts(first) == expected
    assert cold["audit_recoveries"] == 1
    del first

    def read_checked(_):
        assert counts(snapshot()) == expected

    with ThreadPoolExecutor(max_workers=viewers) as workers:
        _, shared = measure(lambda: tuple(workers.map(read_checked, range(viewers))), activity)
    assert shared["audit_recoveries"] == 0

    row = event(history, now)
    expected[row["uid"], row["route"]] += 1
    with audit.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    after, appended = measure(snapshot, activity)
    assert counts(after) == expected
    assert appended["audit_recoveries"] == 1
    return {"cold": cold, "shared_viewer_burst": shared, "single_append": appended}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gateway_data", type=Path, help="Station checkout's src/gateway_data.py")
    parser.add_argument("--events", type=int, choices=(3000, 30000, 74000), required=True)
    parser.add_argument("--viewers", type=int, choices=(1, 16), default=16)
    parser.add_argument("--repeats", type=int, choices=range(1, 8), default=3)
    args = parser.parse_args()
    gateway = load_gateway(args.gateway_data)
    activity = Counter()
    recover = gateway._audit_events

    def observe(*arguments):
        activity["audit_recoveries"] += 1
        return recover(*arguments)

    gateway._audit_events = observe
    with tempfile.TemporaryDirectory(prefix="station-recovery-benchmark-") as directory:
        audit = Path(directory) / "audit.jsonl"
        samples = [replay(gateway, args.events, args.viewers, audit, activity) for _ in range(args.repeats)]
    medians = {phase: {metric: statistics.median(row[phase][metric] for row in samples)
                       for metric in samples[0][phase]} for phase in samples[0]}
    print(json.dumps({"schema": "enchant.station-audit-recovery-baseline.v1",
                      "source_sha256": hashlib.sha256(args.gateway_data.read_bytes()).hexdigest(),
                      "events": args.events, "viewers": args.viewers,
                      "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "scope": "Actual Station snapshot over generated two-UID audit, no ledger. Warm burst includes per-reader validation and thread scheduling.",
                      "exact_totals_and_uid_scopes": True, "samples": samples, "medians": medians}, indent=2))


if __name__ == "__main__":
    main()
