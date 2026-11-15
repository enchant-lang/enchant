#!/usr/bin/env python3
"""Sequential host/control and native POSIX qualification on the pinned tools."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent
DEFAULT_OUT = BASE / "out/host"
TOOLS = json.loads((BASE / "toolchain-pin.json").read_text())
GAMBIT = Path(TOOLS["gambit"])
CLANG = Path(TOOLS["clang"]) / "bin/clang"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="host fixture/build directory; custom output preserves the default generation")
    parser.add_argument("--evidence", type=Path,
                        help="receipt path; custom --out defaults to its own host.json")
    args = parser.parse_args()
    out = args.out.resolve()
    if out == BASE or out in BASE.parents:
        parser.error("host output must not overwrite the Source directory")
    evidence = (args.evidence.resolve() if args.evidence else
                BASE / "evidence/host.json" if out == DEFAULT_OUT.resolve() else out / "host.json")
    out.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.unlink(missing_ok=True)
    sources = ["host.scm", "host/host-values.scm", "host/host-leaves.scm", "host/host-lazy.scm", "host/host-extra.scm"]
    inputs = sources + ["host/native-posix.scm", "fixtures/host-values-check.scm",
                       "fixtures/native-posix-check.scm", "fixtures/host-lazy-check.scm", "fixtures/host-extra-check.scm", "fixtures/ffi-fixture.c",
                       "sdk-pin.json", "toolchain-pin.json", "check-host.py", "host/host-compiler.scm",
                       "host/host-source-frames.scm", "fixtures/host-source-frames-check.scm",
                       "fixtures/host-compiler-cache-check.scm", "fixtures/host-global-cache-check.scm",
                       "fixtures/host-symbol-name-check.scm", "fixtures/host-raw-map-get-check.scm", "fixtures/host-array-check.scm", "fixtures/host-runtime-id-check.scm", "fixtures/host-input-wait-check.scm", "direct/direct-machine.scm",
                       "direct/direct-control-frames.scm", "fixtures/c-critical-boundaries-check.scm",
                       "fixtures/c-critical-continuations-check.scm", "fixtures/c-raw-source-trace-check.scm",
                       "fixtures/c-source-tail-check.scm", "fixtures/c-tail-frame-reuse-check.scm",
                       "direct/direct-shared-raw.scm", "direct/direct-remote.scm", "direct/direct-make-fun.scm",
                       "fixtures/c-plain-procedure-check.scm", "fixtures/c-remote-target-check.scm",
                       "fixtures/c-host-service-check.scm"]
    hashes = {p: digest(BASE / p) for p in inputs}
    runs = []

    def run(label, argv, timeout=60):
        start = time.monotonic()
        result = subprocess.run([str(x) for x in argv], cwd=out, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=timeout)
        (out / (label + ".log")).write_text(result.stdout)
        runs.append({"label": label, "exit": result.returncode,
                     "seconds": round(time.monotonic() - start, 3)})
        if result.returncode:
            raise RuntimeError(label + ": " + result.stdout[-5000:])
        print(label, "PASS", flush=True)
        return result.stdout

    common = "\n".join((BASE / p).read_text() for p in sources)
    (out / "values.scm").write_text(common + "\n" + (BASE / "fixtures/host-values-check.scm").read_text())
    values = run("values-control", [GAMBIT / "bin/gsi", "values.scm"])
    assert "native value/control checks: 27" in values, values
    (out / "lazy.scm").write_text(common + "\n" + (BASE / "fixtures/host-lazy-check.scm").read_text())
    lazy = run("lazy-memo", [GAMBIT / "bin/gsi", "lazy.scm"])
    assert "native lazy memo checks passed" in lazy, lazy
    (out / "extra.scm").write_text(common + "\n" + (BASE / "fixtures/host-extra-check.scm").read_text()
        + "\n" + (BASE / "fixtures/host-symbol-name-check.scm").read_text()
        + "\n" + (BASE / "fixtures/host-raw-map-get-check.scm").read_text()
        + "\n" + (BASE / "fixtures/host-array-check.scm").read_text()
        + "\n" + (BASE / "fixtures/host-runtime-id-check.scm").read_text()
        + "\n" + (BASE / "fixtures/host-input-wait-check.scm").read_text())
    extra = run("storage-and-raw-leaves", [GAMBIT / "bin/gsi", "extra.scm"])
    assert "native extra checks passed" in extra, extra
    assert "NATIVE_LISTS_SPLIT_ABI_PASS 24" in extra, extra
    assert "native symbol-name checks: 15" in extra, extra
    assert "native raw-map-get checks: 19" in extra, extra
    assert "NATIVE_HOST_ARRAY_TUPLE_ABI_PASS 13" in extra, extra
    assert "NATIVE_RUNTIME_ID_ABI_PASS 7" in extra, extra
    assert "NATIVE_OPTIONAL_INPUT_DEADLINE_ABI_PASS 18" in extra, extra
    (out / "source-frames.scm").write_text(common + "\n"
        + (BASE / "host/host-compiler.scm").read_text() + "\n"
        + (BASE / "fixtures/host-compiler-cache-check.scm").read_text() + "\n"
        + (BASE / "fixtures/host-global-cache-check.scm").read_text() + "\n"
        + (BASE / "host/host-source-frames.scm").read_text() + "\n"
        + (BASE / "fixtures/host-source-frames-check.scm").read_text())
    frames = run("source-frames", [GAMBIT / "bin/gsi", "source-frames.scm"], timeout=20)
    assert "native compiler-cache checks: 96" in frames, frames
    assert "native global-cache checks: 48" in frames, frames
    assert "native source-frame checks passed" in frames, frames
    (out / "direct-control.scm").write_text(common + "\n"
        + (BASE / "host/host-compiler.scm").read_text() + "\n"
        + (BASE / "direct/direct-machine.scm").read_text() + "\n"
        + (BASE / "direct/direct-control-frames.scm").read_text() + "\n"
        + (BASE / "fixtures/c-critical-boundaries-check.scm").read_text() + "\n"
        + (BASE / "fixtures/c-critical-continuations-check.scm").read_text() + "\n"
        + (BASE / "fixtures/c-raw-source-trace-check.scm").read_text() + "\n"
        + (BASE / "fixtures/c-source-tail-check.scm").read_text() + "\n"
        + (BASE / "fixtures/c-tail-frame-reuse-check.scm").read_text() + "\n"
        + (BASE / "direct/direct-shared-raw.scm").read_text() + "\n"
        + (BASE / "direct/direct-remote.scm").read_text() + "\n"
        + (BASE / "direct/direct-make-fun.scm").read_text() + "\n"
        + (BASE / "fixtures/c-plain-procedure-check.scm").read_text() + "\n"
        + (BASE / "fixtures/c-remote-target-check.scm").read_text() + "\n"
        + (BASE / "fixtures/c-host-service-check.scm").read_text())
    control = run("direct-control-abi", [GAMBIT / "bin/gsi", "direct-control.scm"], timeout=20)
    for marker in ("NATIVE_C_CRITICAL_BOUNDARIES_PASS 10", "NATIVE_C_CRITICAL_CONTINUATIONS_PASS 18",
                   "NATIVE_C_RAW_SOURCE_TRACE_ABI_PASS 6", "NATIVE_C_SOURCE_TAIL_ABI_PASS 23",
                   "NATIVE_C_TAIL_FRAME_REUSE_ABI_PASS 49", "NATIVE_C_PLAIN_PROCEDURE_ABI_PASS 39",
                   "NATIVE_C_REMOTE_TARGET_ABI_PASS 105", "NATIVE_C_LATE_HOST_SERVICE_ABI_PASS 32"):
        assert marker in control, control
    (out / "posix.scm").write_text(common + "\n" + (BASE / "host/native-posix.scm").read_text()
                                    + "\n" + (BASE / "fixtures/native-posix-check.scm").read_text())
    run("foreign-fixture", [CLANG, "-shared", "-fPIC", BASE / "fixtures/ffi-fixture.c", "-o", "fixture.so"])
    run("posix-to-c", [GAMBIT / "bin/gsc", "-c", "posix.scm"])
    run("posix-link-unit", [GAMBIT / "bin/gsc", "-link", "posix.c"])
    flags = ["-O0", "-fwrapv", "-fno-strict-aliasing", "-fPIC", "-pthread",
             "-D___SINGLE_HOST", "-D___TRUST_C_TCO", "-D___CAN_IMPORT_CLIB_DYNAMICALLY",
             "-D___CAN_IMPORT_SETJMP_DYNAMICALLY", "-I" + str(GAMBIT / "gambit/include")]
    for unit in ["posix", "posix_"]:
        run(unit + "-object", [CLANG, *flags, "-c", unit + ".c", "-o", unit + ".o"])
    run("posix-link", [CLANG, "posix.o", "posix_.o", GAMBIT / "gambit/lib/libgambit.so",
                       "-pthread", "-ldl", "-lm", "-Wl,-rpath," + str(GAMBIT / "gambit/lib"), "-o", "posix"])
    posix = run("posix-clock-readiness-worker", [out / "posix", out / "fixture.so"], timeout=10)
    assert "native POSIX clock/readiness/worker check passed" in posix, posix
    assert hashes == {p: digest(BASE / p) for p in inputs}, "inputs changed during qualification"
    evidence.write_text(json.dumps({"status": "pass", "output": str(out), "scope": "host fixtures; canonical BL gates remain separate",
                                    "inputs": hashes, "tools": TOOLS, "runs": runs,
                                    "values": values, "lazy": lazy, "extra": extra, "source_frames": frames, "direct_control": control, "posix": posix}, indent=2) + "\n")


if __name__ == "__main__":
    main()
