#!/usr/bin/env python3
"""Cheap native-host execution before compiling a full compiler C image.

GSI executes the emitted Scheme with the already compiled native text adapter.
This is a bootstrap preflight, not the C executable/fixpoint qualification.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
OUT = BASE / "out/compiler-closure"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tools = json.loads((BASE / "toolchain-pin.json").read_text())
    sources = ["host.scm", "host/host-values.scm", "host/host-leaves.scm",
               "host/host-lazy.scm", "host/host-extra.scm", "host/host-compiler.scm"]
    pure = "\n".join((BASE / p).read_text() for p in sources)
    host = (OUT / "host.scm").read_text()
    assert host == pure + "\n" + (BASE / "host/native-text.scm").read_text(), "host snapshot is stale"
    addon = OUT / "text.o1"
    cache = json.loads((OUT / "text-addon.json").read_text())
    assert digest(addon) == cache["sha256"]
    prelude = (OUT / "prelude.scm").read_text()
    prefix = ";; BL native compiler. Generated from canonical BL source.\n" + host + "\n"
    assert prelude.startswith(prefix), "prelude host differs from its qualified snapshot"
    interpreted = OUT / "prelude-interpreted.scm"
    interpreted.write_text(pure + "\n(load " + json.dumps(str(addon)) + ")\n" + prelude[len(prefix):])
    program = OUT / "compiler-preflight.scm"
    program.write_text(
        "(load " + json.dumps(str(interpreted)) + ")\n"
        + (BASE / "fixtures/compiler-vector-check.scm").read_text() + "\n"
        + '(native-main (list "--eval" ' + json.dumps(str(OUT / "bundle.scm")) + " "
        + json.dumps(str(BASE / "fixtures/compiler-source.bl")) + "))\n")
    inputs = [OUT / "prelude.scm", OUT / "host.scm", OUT / "bundle.scm", addon,
              BASE / "fixtures/compiler-vector-check.scm", BASE / "fixtures/compiler-source.bl",
              BASE / "toolchain-pin.json", Path(__file__).resolve()]
    hashes = {str(p): digest(p) for p in inputs}
    evidence = BASE / "evidence/compiler-preflight.json"
    evidence.unlink(missing_ok=True)
    result = subprocess.run([tools["gambit"] + "/bin/gsi", str(program)], cwd=BASE.parents[1],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    (OUT / "compiler-preflight.log").write_text(result.stdout)
    print(result.stdout, end="", flush=True)
    assert hashes == {str(p): digest(p) for p in inputs}, "preflight inputs changed"
    report = {"status": "pass" if result.returncode == 0 else "fail", "exit": result.returncode,
              "scope": "emitted Scheme on native GSI host; C compiler/fixpoint remain separate",
              "inputs": hashes, "output": result.stdout}
    evidence.write_text(json.dumps(report, indent=2) + "\n")
    result.check_returncode()
    assert "NATIVE_COMPILER_SOURCE_CORPUS_OK" in result.stdout, "native source corpus did not finish"


if __name__ == "__main__":
    main()
