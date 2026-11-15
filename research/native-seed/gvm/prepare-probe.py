#!/usr/bin/env python3
"""Prefix an observer to an immutable compiler bundle; execute nothing."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("observer", type=Path)
parser.add_argument("bundle", type=Path)
parser.add_argument("out", type=Path)
args = parser.parse_args()
observer, bundle, out = (p.resolve() for p in (args.observer, args.bundle, args.out))
if out.exists() or out in (observer, bundle):
    parser.error("choose a fresh output path")
prefix, original = observer.read_bytes(), bundle.read_bytes()
data = prefix + b"\n" + original
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(data)
assert out.read_bytes()[len(prefix) + 1:] == original
sha = lambda value: hashlib.sha256(value).hexdigest()
receipt = {"schema": "bl.native.gvm-host-probe", "version": 1,
           "status": "prepared-not-executed", "source_qualification": False,
           "inputs": {str(observer): sha(prefix), str(bundle): sha(original),
                      str(Path(__file__).resolve()): sha(Path(__file__).read_bytes())},
           "output": {"path": str(out), "sha256": sha(data)},
           "original_suffix_byte_equal": True, "prefix_bytes": len(prefix),
           "exits_before_macro_bootstrap": True,
           "authored_program_body": False, "installs_host_adapters": False}
out.with_suffix(out.suffix + ".json").write_text(json.dumps(receipt, indent=2) + "\n")
print("NATIVE_GVM_HOST_PROBE_PREPARED")
