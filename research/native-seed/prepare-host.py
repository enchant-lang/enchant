#!/usr/bin/env python3
"""Freeze the seed host and observe its actual registered module/arity keys."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
DEFAULT_OUT = BASE / "out/compiler-closure"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="frozen host/addon/leaf directory; custom output does not replace the default generation")
    parser.add_argument("--evidence", type=Path,
                        help="text/registry receipt; custom --out defaults to its own text-host.json")
    args = parser.parse_args()
    out = args.out.resolve()
    if out == BASE or out in BASE.parents:
        parser.error("host output must not overwrite the Source directory")
    evidence = (args.evidence.resolve() if args.evidence else
                BASE / "evidence/text-host.json" if out == DEFAULT_OUT.resolve() else out / "text-host.json")
    out.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.unlink(missing_ok=True)
    sources = ["host.scm", "host/host-values.scm", "host/host-leaves.scm",
               "host/host-lazy.scm", "host/host-extra.scm", "host/host-compiler.scm"]
    inputs = sources + ["host/native-text.scm", "fixtures/native-text-check.scm", "toolchain-pin.json"]
    hashes = {p: hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in inputs}
    host = "\n".join((BASE / p).read_text() for p in sources)
    text_source = (BASE / "host/native-text.scm").read_text()
    (out / "host.scm").write_text(host + "\n" + text_source)
    gambit = json.loads((BASE / "toolchain-pin.json").read_text())["gambit"]
    addon = out / "text.o1"
    key = hashlib.sha256((hashes["host/native-text.scm"] + hashes["toolchain-pin.json"]).encode()).hexdigest()
    cache = out / "text-addon.json"
    cached = json.loads(cache.read_text()) if cache.exists() else {}
    if not (addon.exists() and cached.get("key") == key
            and cached.get("sha256") == hashlib.sha256(addon.read_bytes()).hexdigest()):
        (out / "text.scm").write_text(text_source)
        result = subprocess.run([gambit + "/bin/gsc", "-dynamic", "-ld-options", "-ldl",
                                 "-o", str(addon), str(out / "text.scm")], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout)
        cache.write_text(json.dumps({"key": key, "sha256": hashlib.sha256(addon.read_bytes()).hexdigest()}))
    load_text = '\n(load ' + json.dumps(str(addon)) + ')\n'
    smoke = out / "text-check.scm"
    smoke.write_text(host + load_text + (BASE / "fixtures/native-text-check.scm").read_text())
    result = subprocess.run([gambit + "/bin/gsi", str(smoke)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stdout)
    assert "native text checks passed" in result.stdout
    print(result.stdout.strip(), flush=True)
    probe = out / "host-registry.scm"
    probe.write_text(host + load_text + '\n(for-each (lambda (row) (display (bl-nth row 0)) (newline)) (native-map-pairs native-leaf-registry))\n')
    result = subprocess.run([gambit + "/bin/gsi", str(probe)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    keys = result.stdout.splitlines()
    assert keys and len(set(keys)) == len(keys) and all(k.rsplit("/", 1)[-1].isdigit() for k in keys)
    assert hashes == {p: hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in inputs}
    (out / "leaves.json").write_text(json.dumps({"registered_leaves": sorted(keys),
                                                 "inputs": hashes,
                                                 "observation": "loaded native host registry"}, indent=2) + "\n")
    print("NATIVE_HOST_LEAVES", len(keys))
    evidence.write_text(json.dumps({"status": "pass", "output": str(out), "host_sha256": hashlib.sha256((out / "host.scm").read_bytes()).hexdigest(), "inputs": hashes,
        "addon": cached if cached.get("key") == key else json.loads(cache.read_text()),
        "checks": "PCRE captures, scan, replacement, grapheme segmentation/reverse/slice, regex split",
        "registered_leaves": len(keys)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
