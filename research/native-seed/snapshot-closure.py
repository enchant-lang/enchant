#!/usr/bin/env python3
"""Copy checked passive closure bytes into a NEW owned generation directory.

No ETF decoding, Source compilation, SDK launch, or mutation of the old capture.
Only location strings in the NEW partition manifest are rebased; raw ETF bytes
and every namespace hash stay exact. The old manifest/closure remain preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(path, expected):
    data = path.read_bytes()
    if len(data) > 33554432 or digest(data) != expected:
        raise RuntimeError("snapshot artifact identity/size mismatch: " + str(path))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    manifest_path = source / "partition.json"
    original_bytes = manifest_path.read_bytes()
    original = json.loads(original_bytes)
    if (original.get("schema") != "bl.native.partitioned-closure" or original.get("version") != 1
            or not 18 <= len(original.get("units", [])) <= 256
            or len({r["namespace"] for r in original["units"]}) != len(original["units"])):
        # The 18-namespace compiler closure, or one extended through
        # update-closure.bl's declared closure additions.
        raise RuntimeError("expected a partitioned compiler-closure parent (18..256 distinct namespaces)")
    if destination.exists():
        raise RuntimeError("snapshot destination must be new: " + str(destination))

    def locate(name):
        path = Path(name)
        return path.resolve() if path.is_absolute() else (source / path).resolve()

    artifact_path = locate(original["artifact_path"])
    artifact = checked(artifact_path, original["artifact_sha256"])
    metadata = checked(locate(original["metadata"]["path"]), original["metadata"]["sha256"])
    units = [(row, checked(locate(row["path"]), row["sha256"])) for row in original["units"]]
    inputs = {str(manifest_path): digest(original_bytes), str(artifact_path): digest(artifact),
              str(locate(original["metadata"]["path"])): digest(metadata)}
    for row, data in units:
        inputs[str(locate(row["path"]))] = digest(data)
    destination.mkdir(parents=True, exist_ok=False)
    parts = destination / "partition"
    parts.mkdir()
    (destination / "closure.etf").write_bytes(artifact)
    (parts / "metadata.etf").write_bytes(metadata)
    result = {**original, "artifact_path": "closure.etf",
              "metadata": {**original["metadata"], "path": "partition/metadata.etf"}, "units": []}
    for index, (row, data) in enumerate(units):
        relative = "partition/unit-" + str(index).zfill(3) + ".etf"
        (destination / relative).write_bytes(data)
        result["units"].append({**row, "path": relative})
    # Historical manifest byte SHA is retained separately from rebased paths.
    (destination / "parent-partition.original.json").write_bytes(original_bytes)
    for name in ("identity.json", "host.scm", "leaves.json"):
        path = source / name
        if not path.is_file():
            raise RuntimeError("snapshot lacks required captured input: " + str(path))
        data = path.read_bytes()
        inputs[str(path)] = digest(data)
        (destination / name).write_bytes(data)
    (destination / "partition.json").write_text(json.dumps(result, indent=2) + "\n")
    for name, expected in inputs.items():
        if digest(Path(name).read_bytes()) != expected:
            raise RuntimeError("snapshot source changed while copying: " + name)
    receipt = {"schema": "bl.native.closure-generation-clone", "version": 1,
        "status": "copied-not-compiled", "source": str(source), "destination": str(destination),
        "original-partition-sha256": digest(original_bytes), "original-artifact-sha256": digest(artifact),
        "new-partition-sha256": digest((destination / "partition.json").read_bytes()),
        "raw-unit-bytes-equal": True, "namespaces": [row["namespace"] for row, _ in units],
        "inputs": inputs, "old-generation-mutated": False, "source-or-anf-interpreted": False}
    (destination / "parent-snapshot.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("NATIVE_CLOSURE_GENERATION_COPIED " + str(destination))


if __name__ == "__main__":
    main()
