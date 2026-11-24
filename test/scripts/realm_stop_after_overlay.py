#!/usr/bin/env python3
"""`bl realm stop` retires a warm checkout VM, also with a library edit overlaid.

Run from an engine checkout whose SDK is prepared for its current tree, with no
VM running (`./bin/bl realm stop` after preparing):

    python3 test/scripts/realm_stop_after_overlay.py

Three phases, each in VMs of their own:

0. Fresh starts: 10 cycles of `bl realm stop`, then two `bl run`. A fresh VM's
   boot and its first request both start `vm-manager`; neither run may print
   `server failed to start` (batch 22: `{:already_started, <vm-manager>}` in
   about 1 of 3 fresh VMs, from a check-then-start in `vm.manager/start`).
   The first run after the stop reaching the stopping VM ("retirement
   pending"; every second cycle of a checkout-root VM on main) is a WARN, or a
   failure with `--strict-stop`.
1. Plain: 23 warm `bl run` of `(println 1)`, then `bl realm stop`.
2. Overlay (U15): an edit to `priv/lib/data/bounded-cache.bl` is present when
   the VM starts, so the warm VM compiles it over the SDK; a few runs, then
   `bl realm stop`. The edit is reverted in `finally`.

Pass (exit 0): in both phases the stop exits 0, prints neither "retirement
pending" nor "retirement failed", and the VM's OS process is gone within 15 s.

Batch 21 failed phase 2: the first stop loaded `reload.generation` inside the
VM manager, that load was refused (`:sdk_runtime_loaded_code_changed`) and
ended the manager, and the VM stayed up. `vm.manager/start` now loads what a
drain calls, and a drain that raises is answered as a refusal with its reason.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BL = ROOT / "bin/bl"
EDITED = ROOT / "priv/lib/data/bounded-cache.bl"


def checkout_vms():
    """OS pids of BEAMs serving this checkout (their environment names it)."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if not os.readlink(entry / "exe").endswith("beam.smp"):
                continue
            environ = (entry / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        if f"BL_CHECKOUT_ROOT={ROOT}".encode() in environ:
            found.append(int(entry.name))
    return sorted(found)


def bl(*argv, timeout=600):
    return subprocess.run([str(BL), *argv], cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def stop_and_check(label):
    vms = checkout_vms()
    result = bl("realm", "stop")
    output = result.stdout + result.stderr
    print(f"{label}: realm stop exit {result.returncode}: {output.strip().splitlines()[-1:]}", flush=True)
    failures = []
    if result.returncode != 0:
        failures.append(f"{label}: realm stop exited {result.returncode}")
    for marker in ("retirement pending", "retirement failed"):
        if marker in output:
            failures.append(f"{label}: realm stop printed {marker!r}:\n{output}")
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and any(pid in checkout_vms() for pid in vms):
        time.sleep(0.2)
    left = [pid for pid in vms if pid in checkout_vms()]
    if left:
        failures.append(f"{label}: VM {left} still running 15 s after realm stop")
    return failures


def kill_vms():
    for pid in checkout_vms():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def main():
    if checkout_vms():
        sys.exit(f"a VM already serves {ROOT}; run `./bin/bl realm stop` first")
    original = EDITED.read_bytes()
    failures = []
    # `--strict-stop` also fails on a run that reaches a VM `realm stop` has
    # answered for but that still serves (an open defect on main, reported
    # separately); without it those are printed as warnings.
    strict_stop = "--strict-stop" in sys.argv[1:]
    warnings = []
    with tempfile.TemporaryDirectory(prefix="bl-realm-stop-") as scratch:
        program = Path(scratch) / "one.bl"
        program.write_text("(println 1)\n")
        try:
            for cycle in range(10):
                before = checkout_vms()
                bl("realm", "stop")
                runs = [bl("run", str(program))]
                # A stop that answers while its VM still serves sends the next
                # run into a draining VM. Reported on its own; that cycle's
                # fresh-start check runs once the old VM is gone.
                if "retirement pending" in runs[0].stdout + runs[0].stderr:
                    warnings.append(f"stop-then-run: cycle {cycle}: the run after realm stop reached the stopping VM")
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline and any(pid in checkout_vms() for pid in before):
                        time.sleep(0.2)
                    runs = [bl("run", str(program))]
                runs.append(bl("run", str(program)))
                for r in runs:
                    output = r.stdout + r.stderr
                    if "server failed to start" in output:
                        failures.append(f"fresh: cycle {cycle}: {output.strip()}")
                    elif r.returncode != 0:
                        failures.append(f"fresh: cycle {cycle}: run exit {r.returncode}:\n{output}")
            print(f"fresh: 10 stop/run/run cycles, {len(failures)} failure(s)", flush=True)
            bl("realm", "stop")
            kill_vms()

            for _ in range(23):
                r = bl("run", str(program))
                if r.returncode != 0:
                    failures.append(f"plain: run failed: {r.stdout}{r.stderr}")
                    break
            failures += stop_and_check("plain")
            kill_vms()

            EDITED.write_bytes(original + b"\n; realm_stop_after_overlay.py: a library edit the warm VM overlays\n")
            for _ in range(3):
                # The overlay may refuse this edit (a running owner holds the
                # code); the stop must retire the VM either way.
                bl("run", str(program))
            if not checkout_vms():
                failures.append("overlay: no VM was started")
            failures += stop_and_check("overlay")
        finally:
            EDITED.write_bytes(original)
            kill_vms()
    for warning in warnings:
        print("WARN " + warning)
    if strict_stop:
        failures += warnings
    if failures:
        print("FAIL\n" + "\n".join(failures))
        sys.exit(1)
    print("PASS realm stop retires the VM, plain and with a library overlay")


if __name__ == "__main__":
    main()
