#!/usr/bin/env python3
"""Compile validated GVM DATA through the pinned backend, then C and LLVM.

This is a build checkpoint, never a Source/self-hosting qualification. Run
under a memory-capped systemd scope; each compiler child keeps its 120s limit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
FLAGS = ["-O1", "-fwrapv", "-fno-strict-aliasing", "-fno-trapping-math",
         "-fno-math-errno", "-fPIC", "-fno-common", "-D___SINGLE_HOST",
         "-D___TRUST_C_TCO", "-D___CAN_IMPORT_CLIB_DYNAMICALLY",
         "-D___CAN_IMPORT_SETJMP_DYNAMICALLY", "-D___DYNAMIC"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    data, out = args.data.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "llvm").mkdir(exist_ok=True)
    tools = json.loads((BASE / "toolchain-pin.json").read_text())
    gambit = Path(tools["gambit"])
    clang = str(Path(tools["clang"]) / "bin/clang")
    importer, reader = BASE / "gvm/import.scm", BASE / "gvm/reader-check.scm"
    c, obj = out / "module.c", out / "module.o1"
    ir, llvm_obj = out / "llvm/module.ll", out / "llvm/module.o1"
    receipt = {"schema": "bl.native.gvm-module-build", "version": 1,
               "status": "building", "qualification": False,
               "inputs": {str(p): digest(p) for p in
                          (Path(__file__), data, importer, reader, BASE / "toolchain-pin.json")},
               "tools": tools, "flags": FLAGS, "child_deadline_seconds": 120,
               "jobs": []}

    def save():
        (out / "build.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(name, command, env=None):
        start = time.monotonic()
        row = {"name": name, "argv": command}
        receipt["jobs"].append(row)
        save()
        with (out / (name + ".log")).open("w") as log:
            try:
                result = subprocess.run(command, cwd=ROOT, env=env,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=120)
                row["returncode"] = result.returncode
                row["seconds"] = time.monotonic() - start
                save()
                if result.returncode:
                    raise RuntimeError(f"{name} failed; see {log.name}")
            except subprocess.TimeoutExpired:
                row.update(status="timeout", seconds=time.monotonic() - start)
                raise

    q = json.dumps  # Paths are Scheme string literals, never shell source.
    expression = ("(with-exception-catcher (lambda(e)(display-exception e)(exit 1)) "
                  "(lambda() (load " + q(str(importer)) + ") (load " + q(str(reader)) + ") "
                  "(gvm-import-main " + q(str(data)) + " " + q(str(c)) + ' "module.o1") (exit 0)))')
    env = dict(os.environ, BL_GVM_READ_PROBE_DIR=str(out))
    try:
        run("import", [str(gambit / "bin/gsc"), "-e", expression], env)
        common = [clang, *FLAGS, "-I" + str(gambit / "gambit/include")]
        run("c", [*common, "-shared", "-rdynamic", str(c), "-ldl", "-lm", "-o", str(obj)])
        run("llvm-ir", [*common, "-S", "-emit-llvm", str(c), "-o", str(ir)])
        run("llvm-link", [clang, "-O1", "-fPIC", "-shared", "-rdynamic", str(ir),
                          "-ldl", "-lm", "-o", str(llvm_obj)])
        receipt["artifacts"] = {str(p): {"sha256": digest(p), "bytes": p.stat().st_size}
                                for p in (c, obj, ir, llvm_obj)}
        receipt["status"] = "compiled-not-qualified"
        print("NATIVE_GVM_MODULE_C_AND_LLVM_COMPILED", flush=True)
    except BaseException as error:
        receipt.update(status="failed", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
