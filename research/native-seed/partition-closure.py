#!/usr/bin/env python3
"""Partition an owned compiler ETF without decoding terms or changing syntax.

The closure exceeds the public per-value node limit. Every metadata field and
namespace unit keeps that limit; no compiler data limit is increased.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
OUT = BASE / "out/compiler-closure"


class ETF:
    def __init__(self, data):
        assert len(data) <= 33554432 and data[0] == 131, "invalid artifact envelope"
        self.data = data

    def integer(self, offset, width):
        assert offset + width <= len(self.data), "truncated size"
        return int.from_bytes(self.data[offset:offset + width], "big")

    def span(self, start):
        offset, nodes, pending = start, 0, [(1, 0)]
        while pending:
            count, depth = pending.pop()
            assert depth <= 128 and count > 0 and nodes < 1000000, "unit exceeds structural bounds"
            if count > 1:
                pending.append((count - 1, depth))
            tag = self.integer(offset, 1)
            offset += 1
            nodes += 1
            children = 0
            if tag == 97:
                offset += 1
            elif tag == 98:
                offset += 4
            elif tag == 70:
                offset += 8
            elif tag in (100, 118, 107):
                size = self.integer(offset, 2)
                offset += 2 + size
            elif tag in (115, 119):
                size = self.integer(offset, 1)
                offset += 1 + size
            elif tag == 109:
                size = self.integer(offset, 4)
                offset += 4 + size
            elif tag == 104:
                children = self.integer(offset, 1)
                offset += 1
            elif tag in (105, 108, 116):
                children = self.integer(offset, 4)
                offset += 4
                if tag == 108:
                    children += 1
                elif tag == 116:
                    children *= 2
            elif tag == 106:
                pass
            elif tag in (110, 111):
                width = 1 if tag == 110 else 4
                size = self.integer(offset, width)
                offset += width + 1 + size
            else:
                raise ValueError(f"artifact contains excluded ETF tag {tag} at {offset - 1}")
            assert offset <= len(self.data), "truncated payload"
            if children:
                assert children <= 1000000 - nodes, "oversized child group"
                pending.append((children, depth + 1))
        return offset

    def text(self, start, atom=False):
        tag = self.integer(start, 1)
        width = 1 if tag in (115, 119) else 2 if tag in (100, 118) else 4
        assert tag in ((100, 118, 115, 119) if atom else (109,)), "invalid map key"
        size = self.integer(start + 1, width)
        return self.data[start + 1 + width:start + 1 + width + size].decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT, help="owned closure directory (input closure.etf and output partitions)")
    out = parser.parse_args().out.resolve()
    source = out / "closure.etf"
    data = source.read_bytes()
    etf = ETF(data)
    assert data[1] == 116 and 1 <= etf.integer(2, 4) <= 32, "closure must be a small map"
    offset, fields, units, names = 6, [], [], set()
    target = out / "partition"
    target.mkdir(exist_ok=True)

    def write(name, raw):
        path = target / name
        path.write_bytes(raw)
        return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}

    for _ in range(etf.integer(2, 4)):
        start = offset
        key_end = etf.span(start)
        key = etf.text(start, atom=True)
        assert key not in names, "duplicate closure key"
        names.add(key)
        if key == "units":
            assert data[key_end] == 116, "unit table must be a map"
            count = etf.integer(key_end + 1, 4)
            assert 1 <= count <= 256, "unit count bound"
            offset = key_end + 5
            unit_names = set()
            for _ in range(count):
                end = etf.span(offset)
                ns = etf.text(offset)
                assert re.fullmatch(r"[A-Za-z0-9_.-]+", ns) and ns not in unit_names, "invalid namespace"
                unit_names.add(ns)
                offset = etf.span(end)
                units.append({"namespace": ns, **write(ns + ".etf", b"\x83" + data[end:offset])})
        else:
            offset = etf.span(key_end)
            fields.append(data[start:offset])
    assert offset == len(data) and "units" in names, "trailing data or missing unit table"
    metadata = write("metadata.etf", b"\x83\x74" + len(fields).to_bytes(4, "big") + b"".join(fields))
    manifest = {"schema": "bl.native.partitioned-closure", "version": 1,
                "artifact_sha256": hashlib.sha256(data).hexdigest(), "artifact_path": str(source.resolve()),
                "metadata": metadata, "units": units}
    (out / "partition.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("NATIVE_PARTITION", len(units), "bounded units; original", manifest["artifact_sha256"])


if __name__ == "__main__":
    main()
