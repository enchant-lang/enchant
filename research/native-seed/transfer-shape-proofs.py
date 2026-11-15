#!/usr/bin/env python3
"""Transfer existing SDK-bound shape proofs only for byte-identical owned parts.

No Source/ETF decoding or authority grant. native.artifact independently checks
the copied key against its exact current SDK/bytes/policy before using a proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    value = json.loads(path.read_text())
    if value.get("schema") != "bl.native.partitioned-closure" or value.get("version") != 1:
        raise RuntimeError("unsupported owned partition manifest")
    return value


def locate(manifest, record):
    path = Path(record["path"])
    return path.resolve() if path.is_absolute() else (manifest.parent / path).resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_manifest", type=Path)
    parser.add_argument("new_manifest", type=Path)
    parser.add_argument("--sdk-pin", type=Path, default=Path("research/native-seed/sdk-pin.json"))
    args = parser.parse_args()
    old_path, new_path = args.old_manifest.resolve(), args.new_manifest.resolve()
    old, new = load(old_path), load(new_path)
    pin = json.loads(args.sdk_pin.read_text())
    descriptor = (Path(pin["sdk"]) / "artifact.json").read_bytes()
    if sha(descriptor) != pin["descriptor_sha256"]:
        raise RuntimeError("qualified SDK descriptor changed")
    old_rows = {r["namespace"]: r for r in old["units"]}
    new_rows = {r["namespace"]: r for r in new["units"]}
    old_rows["@metadata"], new_rows["@metadata"] = old["metadata"], new["metadata"]
    copied = 0
    for namespace, row in new_rows.items():
        previous = old_rows.get(namespace)
        if not previous or row["sha256"] != previous["sha256"]:
            continue
        source, destination = locate(old_path, previous), locate(new_path, row)
        if not destination.is_relative_to(new_path.parent) or source == destination:
            raise RuntimeError("proof destination is not a distinct owned new-generation part")
        old_bytes, new_bytes = source.read_bytes(), destination.read_bytes()
        if (len(old_bytes) > 33554432 or sha(old_bytes) != row["sha256"]
                or sha(new_bytes) != row["sha256"] or old_bytes != new_bytes):
            raise RuntimeError("owned part changed while transferring proof")
        proof_path = Path(str(source) + ".validated.json")
        if not proof_path.is_file():
            continue
        proof_bytes = proof_path.read_bytes()
        if len(proof_bytes) > 65536:
            raise RuntimeError("shape proof exceeds its passive JSON bound")
        proof = json.loads(proof_bytes)
        if (proof.get("schema") != "bl.native.partition-shape-proof" or proof.get("version") != 1
                or proof.get("partition_sha256") != row["sha256"]
                or proof.get("policy") != "canonical-closed-etf-and-compiler-data-v1"
                or proof.get("sdk_descriptor_sha256") != pin["descriptor_sha256"]
                or not re.fullmatch("[0-9a-f]{64}", proof.get("key", ""))):
            continue
        Path(str(destination) + ".validated.json").write_bytes(proof_bytes)
        copied += 1
    print("NATIVE_IDENTICAL_PART_PROOFS_COPIED " + str(copied))


if __name__ == "__main__":
    main()
