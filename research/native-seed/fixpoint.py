#!/usr/bin/env python3
"""Sequential native compiler gates; stage zero must already be exported.

Stage 1 is the seed-compiled canonical BL compiler. It reads bundle.scm's
ORIGINAL BL sources to emit stage2.scm; compiled stage 2 emits stage3.scm.
No bl executable, BEAM, JavaScript compiler, or ANF interpreter is launched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    evidence = out / "fixpoint.json"
    evidence.unlink(missing_ok=True)
    tools = json.loads((root / "research/native-seed/toolchain-pin.json").read_text())
    gambit = Path(tools["gambit"])
    clang = Path(tools["clang"]) / "bin/clang"
    inputs = [out / p for p in ("stage1.scm", "bundle.scm", "host.scm", "identity.json")]
    inputs += [args.corpus.resolve(), Path(__file__).resolve(), root / "research/native-seed/toolchain-pin.json"]
    for path in inputs:
        if not path.is_file():
            raise RuntimeError(f"missing qualified stage-zero input: {path}")
    runs = []

    def run(label, argv):
        start = time.monotonic()
        argv = [str(x) for x in argv]
        result = subprocess.run(argv, cwd=out, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=args.timeout)
        (out / f"{label}.log").write_text(result.stdout)
        runs.append({"label": label, "argv": argv, "seconds": round(time.monotonic() - start, 3),
                     "exit": result.returncode})
        if result.returncode:
            raise RuntimeError(f"{label}: exit {result.returncode}\n{result.stdout[-5000:]}")
        print(label, "PASS", flush=True)
        return result.stdout

    def compile_native(name):
        run(name + "-scheme-to-c", [gambit / "bin/gsc", "-c", name + ".scm"])
        run(name + "-link-unit", [gambit / "bin/gsc", "-link", name + ".c"])
        flags = ["-O0", "-fwrapv", "-fno-strict-aliasing", "-fPIC", "-pthread", "-D___SINGLE_HOST",
                 "-D___TRUST_C_TCO", "-D___CAN_IMPORT_CLIB_DYNAMICALLY",
                 "-D___CAN_IMPORT_SETJMP_DYNAMICALLY", "-I" + str(gambit / "gambit/include")]
        objects = []
        for unit in (name, name + "_"):
            run(unit + "-object", [clang, *flags, "-c", unit + ".c", "-o", unit + ".o"])
            objects.append(unit + ".o")
        run(name + "-native-link", [clang, *objects, gambit / "gambit/lib/libgambit.so", "-pthread", "-ldl", "-lm",
                                   "-Wl,-rpath," + str(gambit / "gambit/lib"), "-o", name])
        return out / name

    stage1 = compile_native("stage1")
    corpus1 = run("stage1-source-corpus", [stage1, "--eval", out / "bundle.scm", args.corpus.resolve()])
    if "NATIVE_COMPILER_SOURCE_CORPUS_OK" not in corpus1:
        raise RuntimeError("source corpus did not witness native compilation and execution")
    run("stage1-builds-stage2", [stage1, "--compile", out / "bundle.scm", out / "host.scm", out / "stage2.scm"])
    stage2 = compile_native("stage2")
    corpus2 = run("stage2-source-corpus", [stage2, "--eval", out / "bundle.scm", args.corpus.resolve()])
    if corpus1 != corpus2:
        raise RuntimeError("stage 1 and stage 2 source semantics differ")
    run("stage2-builds-stage3", [stage2, "--compile", out / "bundle.scm", out / "host.scm", out / "stage3.scm"])
    h2, h3 = digest(out / "stage2.scm"), digest(out / "stage3.scm")
    if h2 != h3 or (out / "stage2.scm").read_bytes() != (out / "stage3.scm").read_bytes():
        raise RuntimeError("native bootstrap did not reach a stage 2 / 3 Scheme artifact fixpoint")
    report = {"schema": "bl.native.bootstrap-fixpoint", "version": 1,
              "status": "qualified", "stage0": "canonical BL compiler captured once on qualified SDK",
              "stage1": "canonical BL reader/compiler/emitter compiled through Scheme and C",
              "stage2": "compiled from original BL source by native stage1",
              "stage3": "compiled from original BL source by native stage2",
              "stage2-sha256": h2, "stage3-sha256": h3, "stage2-stage3-byte-equal": True,
              "stage1-stage2-source-corpus-equal": True,
              "inputs": {str(p): digest(p) for p in inputs}, "runs": runs}
    evidence.write_text(json.dumps(report, indent=2) + "\n")
    print("NATIVE_BOOTSTRAP_FIXPOINT", h2, flush=True)


if __name__ == "__main__":
    main()
