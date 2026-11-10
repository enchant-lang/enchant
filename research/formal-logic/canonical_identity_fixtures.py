"""Independent ETF fixtures for the explicitly tagged canonical normal form.

This specifies chosen normal forms directly. It does not classify BL runtime
values or use the production normalizer. No Erlang runtime is started.
"""
from pathlib import Path
import hashlib
import json
import struct


def encode(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    if isinstance(value, bytes):
        return b"m" + len(value).to_bytes(4, "big") + value
    if isinstance(value, int):
        if 0 <= value <= 255:
            return b"a" + bytes([value])
        if -(2**31) <= value < 2**31:
            return b"b" + value.to_bytes(4, "big", signed=True)
        size = (abs(value).bit_length() + 7) // 8
        assert size < 256
        return b"n" + bytes([size, int(value < 0)]) + abs(value).to_bytes(size, "little")
    if isinstance(value, tuple):
        assert len(value) < 256
        return b"h" + bytes([len(value)]) + b"".join(map(encode, value))
    if isinstance(value, list):
        return b"j" if not value else b"l" + len(value).to_bytes(4, "big") + b"".join(map(encode, value)) + b"j"
    raise TypeError(value)


normal_forms = {
    "nil": ("nil",),
    "false": ("bool", 0),
    "big-negative": ("int", -12345678901234567890123),
    "half": ("float64", b"\x83F" + struct.pack(">d", 0.5)),
    "keyword": ("keyword", "a/b"),
    "symbol": ("symbol", "a/b"),
    "vector": ("vector", [("int", 1), ("binary", "x"), ("keyword", "k")]),
    "map": ("map", [(("keyword", "a"), ("int", 1)), (("keyword", "b"), ("bool", 0))]),
}
records = []
for name, form in normal_forms.items():
    wire = b"\x83" + encode(("bl/canonical-formal-data-v1", form))
    records.append({"id": name, "etf_hex": wire.hex(), "sha256": hashlib.sha256(wire).hexdigest()})
output = Path(__file__).parent / "evidence/contexts/canonical-fixtures.json"
output.write_text(json.dumps({"schema": "enchant.formal.canonical-byte-fixtures.v1", "records": records}, indent=2) + "\n")
