#!/usr/bin/env python3
"""`bl realm stop` retires a warm checkout VM, also with a library edit overlaid.

Run from an engine checkout whose SDK is prepared for its current tree, with no
VM running (`./bin/bl realm stop` after preparing):

    python3 test/scripts/realm_stop_after_overlay.py

Two phases, each in a VM of its own:

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
    with tempfile.TemporaryDirectory(prefix="bl-realm-stop-") as scratch:
        program = Path(scratch) / "one.bl"
        program.write_text("(println 1)\n")
        try:
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
    if failures:
        print("FAIL\n" + "\n".join(failures))
        sys.exit(1)
    print("PASS realm stop retires the VM, plain and with a library overlay")


if __name__ == "__main__":
    main()
