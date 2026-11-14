#!/usr/bin/env python3
"""Execute the original source corpus with the already compiled native image."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

BASE = Path(__file__).resolve().parent
OUT = BASE / "out/compiler-closure"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = BASE / "evidence/native-compiler.json"
    evidence.unlink(missing_ok=True)
    report = {"status": "running", "scope": "compiled canonical compiler reads and executes original BL source",
              "self_hosted": False, "self_emission_and_fixpoint": "separate gates", "deadline_seconds": 120}
    process = None
    started = time.monotonic()
    try:
        build = json.loads((OUT / "native-build.json").read_text())
        assert build["status"] == "stage1-compiled-not-qualified"
        image = OUT / "stage1"
        stage = build["builds"][-1]
        assert stage["stage"] == "stage1"
        assert digest(image) == stage["executable_sha256"]
        assert digest(OUT / "stage1.scm") == stage["source_sha256"]
        for name, expected in build["inputs"].items():
            assert digest(Path(name)) == expected, "build input changed: " + name
        paths = [image, OUT / "stage1.scm", OUT / "bundle.scm", OUT / "native-build.json",
                 BASE / "fixtures/compiler-source.bl", Path(__file__).resolve()]
        hashes = {str(p): digest(p) for p in paths}
        report["inputs"] = hashes
        report["native_build"] = {"units": len(stage["units"]),
                                  "reused_objects": sum(row["reused_object"] for row in stage["units"])}
        argv = [str(image), "--eval", str(OUT / "bundle.scm"), str(BASE / "fixtures/compiler-source.bl")]
        report["argv"] = argv
        process = subprocess.Popen(argv, cwd=BASE.parents[1], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, start_new_session=True)
        try:
            output, _ = process.communicate(timeout=120)
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
            (OUT / "stage1-source-probe.log").write_text(output)
            raise
        (OUT / "stage1-source-probe.log").write_text(output)
        print(output, end="", flush=True)
        report.update({"exit": process.returncode, "output": output})
        assert hashes == {str(p): digest(p) for p in paths}, "compiler inputs changed"
        assert process.returncode == 0, "native source corpus failed"
        for marker in ("NATIVE_MULTI_SELF_DISPATCH_OK", "NATIVE_SINGLE_SELF_IDENTITY_OK",
                       "NATIVE_COMPILER_SOURCE_CORPUS_OK"):
            assert output.splitlines().count(marker) == 1, "missing source witness: " + marker
        report["status"] = "pass"
    except BaseException as error:
        report.update({"status": "fail", "error": str(error)})
        raise
    finally:
        report["seconds"] = round(time.monotonic() - started, 3)
        evidence.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
