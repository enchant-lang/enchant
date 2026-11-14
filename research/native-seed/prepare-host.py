#!/usr/bin/env python3
"""Freeze the seed host and observe its actual registered module/arity keys."""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
OUT = BASE / "out/compiler-closure"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = ["host.scm", "host/host-values.scm", "host/host-leaves.scm",
               "host/host-lazy.scm", "host/host-extra.scm", "host/host-compiler.scm"]
    hashes = {p: hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in sources}
    host = "\n".join((BASE / p).read_text() for p in sources)
    (OUT / "host.scm").write_text(host)
    probe = OUT / "host-registry.scm"
    probe.write_text(host + '\n(for-each (lambda (row) (display (bl-nth row 0)) (newline)) (native-map-pairs native-leaf-registry))\n')
    gambit = json.loads((BASE / "toolchain-pin.json").read_text())["gambit"]
    result = subprocess.run([gambit + "/bin/gsi", str(probe)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    keys = result.stdout.splitlines()
    assert keys and len(set(keys)) == len(keys) and all(k.rsplit("/", 1)[-1].isdigit() for k in keys)
    assert hashes == {p: hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in sources}
    (OUT / "leaves.json").write_text(json.dumps({"registered_leaves": sorted(keys),
                                                 "inputs": hashes,
                                                 "observation": "loaded native host registry"}, indent=2) + "\n")
    print("NATIVE_HOST_LEAVES", len(keys))


if __name__ == "__main__":
    main()
