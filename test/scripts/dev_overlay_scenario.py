#!/usr/bin/env python3
"""U15 gate: a priv/lib edit runs in the warm checkout VM without an SDK.

Run from an engine checkout whose SDK is prepared for its current tree, with no
VM running (`./bin/bl realm stop` after preparing):

    python3 test/scripts/dev_overlay_scenario.py

It edits `priv/lib/split/wire.bl` (`wire-text-length`, which the library
namespace `split.web` calls in `decode`), runs a `bl test` that exercises the
library-to-library call, reverts the edit and runs the SDK expectation again.
It edits `priv/lib/data/bounded-cache.bl` while a cache owner (its
`defserver owner`) runs: the unit is held whole with a once-per-digest note and
commands keep running. Then it shows that a compiler-key source (`priv/std/multi.bl`) is refused with
a message instead of looking fresh. Every edit is reverted in `finally`.

Pass: exit 0. Each step prints its wall time. It checks, for the edit:
  * the next `bl test` sees it in under 10 s;
  * the same VM answered (same OS pid), no `.bl/sdks/<fingerprint>` directory
    and no preparation unit appeared, `current-sdk` did not move;
and, after the revert, that the SDK's code answers again.
"""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BL = ROOT / "bin/bl"
WIRE = ROOT / "priv/lib/split/wire.bl"
MULTI = ROOT / "priv/std/multi.bl"
CACHE = ROOT / "priv/lib/data/bounded-cache.bl"
CACHE_PROBE = """(ns u15-probe-cache-test (:require [data.bounded-cache]))
(deftest a-cache-owner-runs
  (is (= true (data.bounded-cache/ready! :u15_scenario_cache))))
"""
NEEDLE = "(erlang/length (unicode/characters_to_list s))"
EDIT = "(+ 0 0)"

PROBE = """(ns u15-probe-{name}-test (:require [split.web]))
(deftest library-call-{name}
  (is (= {expect} (try (split.web/decode {{}} [:text 0 3] "abcd" 0) (catch _ :refused)))))
"""


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


def preparation_units():
    out = subprocess.run(["systemctl", "--user", "list-units", "--no-legend", "--plain",
                          "foundry-artifact-job_*", "bl-checkout-*"],
                         stdout=subprocess.PIPE, text=True).stdout
    return sorted(line.split()[0] for line in out.splitlines() if line.strip())


def sdk_state():
    sdks = ROOT / ".bl/sdks"
    return (sorted(p.name for p in sdks.iterdir() if p.is_dir()),
            os.path.realpath(sdks / "current-sdk"))


def bl_test(project, name, label):
    started = time.monotonic()
    result = subprocess.run([str(BL), "test", f"{name}_test.bl"], cwd=project,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=900)
    elapsed = time.monotonic() - started
    tail = "\n".join(result.stdout.strip().splitlines()[-6:])
    print(f"== {label}: exit {result.returncode} in {elapsed:.2f} s\n{tail}", flush=True)
    return result.returncode, elapsed, result.stdout


def main():
    failures = []

    def check(ok, what):
        print(("PASS " if ok else "FAIL ") + what, flush=True)
        if not ok:
            failures.append(what)

    original_wire = WIRE.read_bytes()
    original_multi = MULTI.read_bytes()
    if NEEDLE.encode() not in original_wire:
        raise SystemExit(f"{WIRE} no longer has the probed expression {NEEDLE}")
    project = Path(tempfile.mkdtemp(prefix="u15-probe-"))
    (project / "sdk_test.bl").write_text(PROBE.format(name="sdk", expect=":refused"))
    (project / "edit_test.bl").write_text(PROBE.format(name="edit", expect='"abcd"'))
    (project / "cache_test.bl").write_text(CACHE_PROBE)
    original_cache = CACHE.read_bytes()
    try:
        code, _, _ = bl_test(project, "sdk", "baseline (starts or reuses the VM)")
        check(code == 0, "the SDK's split.wire refuses four codepoints in a [:text 0 3]")
        vms, units, sdks = checkout_vms(), preparation_units(), sdk_state()
        print(f"   VM pids {vms}; preparation units {units}")
        code, _, _ = bl_test(project, "sdk", "baseline, warm")
        check(code == 0, "warm baseline")

        WIRE.write_bytes(original_wire.replace(NEEDLE.encode(), EDIT.encode()))
        code, elapsed, _ = bl_test(project, "edit", "after editing priv/lib/split/wire.bl")
        check(code == 0, "split.web/decode (a library caller) runs the edited wire-text-length")
        check(elapsed < 10, f"the edit is seen in under 10 s ({elapsed:.2f} s)")
        check(checkout_vms() == vms, f"the same VM answered ({checkout_vms()} == {vms})")
        check(preparation_units() == units, "no SDK preparation unit started")
        check(sdk_state() == sdks, "no new SDK fingerprint directory; current-sdk unchanged")
        code, elapsed, _ = bl_test(project, "edit", "edited, warm again")
        check(code == 0, "the edit stays applied")

        WIRE.write_bytes(original_wire)
        code, elapsed, _ = bl_test(project, "sdk", "after reverting the edit")
        check(code == 0, "the revert restores the SDK's code")
        check(elapsed < 10, f"the revert is seen in under 10 s ({elapsed:.2f} s)")
        check(checkout_vms() == vms and preparation_units() == units and sdk_state() == sdks,
              "still the same VM and SDK, no preparation")

        # A unit whose server owner is running (data.bounded-cache defines
        # `defserver owner`) cannot be swapped: it is held whole, with a note,
        # and the command runs on the SDK's code. Before the fix every command
        # failed with :code_leased after a half-applied unit, and recompiled.
        code, _, _ = bl_test(project, "cache", "start a bounded-cache owner")
        check(code == 0, "a data.bounded-cache owner runs in the warm VM")
        CACHE.write_bytes(original_cache + b"\n(defn u15-scenario-probe [] :edited)\n")
        code, elapsed, out = bl_test(project, "cache", "after editing priv/lib/data/bounded-cache.bl")
        check(code == 0, "the command still runs while the owner's unit is held")
        check("bounded-cache.bl" in out and "cannot be replaced in the warm VM" in out, "and says which unit and why")
        check("code_leased" not in out and "did not compile" not in out, "no :code_leased failure")
        code, again, out = bl_test(project, "cache", "held unit, next command")
        check(code == 0 and "cannot be replaced in the warm VM" not in out, "the note is shown once per digest")
        check(again < 10, f"a held unit costs nothing on the next command ({again:.2f} s)")
        CACHE.write_bytes(original_cache)
        code, _, _ = bl_test(project, "sdk", "after reverting bounded-cache.bl")
        check(code == 0, "the tree is back on the SDK's code")

        # A compiler-key source is an engine input: selection says so. Hold the
        # preparation lock so the selection cannot start a preparation.
        MULTI.write_bytes(original_multi + b"\n;; u15 probe\n")
        with open(ROOT / ".bl/sdks/preparation.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            env = dict(os.environ, BL_SDK_LOCK_WAIT="0")
            env.pop("BL_SDK_REUSE_CURRENT", None)
            started = time.monotonic()
            result = subprocess.run([str(ROOT / "scripts/prepare-checkout-sdk"), "--selection"], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
            print(f"== compiler-key edit, selection: exit {result.returncode} in {time.monotonic() - started:.2f} s\n"
                  + result.stderr.strip())
        check(result.returncode == 75 and result.stdout == "", "selection did not reuse the SDK for a compiler input")
        check("priv/std/multi.bl feeds the compiler key" in result.stderr, "and says why")
    finally:
        WIRE.write_bytes(original_wire)
        MULTI.write_bytes(original_multi)
        CACHE.write_bytes(original_cache)
        # The probe's VM is this scenario's: stop it (from the directory that
        # started it) rather than leave it holding memory.
        subprocess.run([str(BL), "realm", "stop"], cwd=project, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=120)
        shutil.rmtree(project, ignore_errors=True)
    print("FAILED: " + "; ".join(failures) if failures else "U15 scenario passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
