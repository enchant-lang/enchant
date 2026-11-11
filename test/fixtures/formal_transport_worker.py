#!/usr/bin/env python3
"""Deliberately faulty framed-ETF peer; never a solver or proof checker.

The BL test copies this executable under a case name. Every packet and EOF is
recorded beside that copy. Hanging cases keep reading stdin, so the test can
observe whether closing the owning port really reaches the OS process.
"""
import json
import os
from pathlib import Path
import struct
import sys
import zlib


class Atom(str):
    pass


def etf(value):
    if isinstance(value, Atom):
        raw = value.encode()
        return b"w" + bytes([len(raw)]) + raw
    if isinstance(value, bool):
        return etf(Atom(str(value).lower()))
    if isinstance(value, int):
        return b"b" + struct.pack(">i", value)
    if isinstance(value, str):
        raw = value.encode()
        return b"m" + struct.pack(">I", len(raw)) + raw
    if isinstance(value, dict):
        return b"t" + struct.pack(">I", len(value)) + b"".join(etf(k) + etf(v) for k, v in value.items())
    raise TypeError(type(value))


path = Path(sys.argv[0])
mode = path.name
backend = sys.argv[sys.argv.index("--backend") + 1]
log = {"pid": os.getpid(), "mode": mode, "packets": 0, "eof": False}


def record():
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(log))
    temporary.replace(path.with_suffix(".json"))


def read_exact(n):
    data = bytearray()
    while len(data) < n:
        chunk = sys.stdin.buffer.read(n - len(data))
        if not chunk:
            log["eof"] = True
            record()
            sys.exit(0)
        data.extend(chunk)
    return bytes(data)


record()
while True:
    read_exact(struct.unpack(">I", read_exact(4))[0])
    log["packets"] += 1
    record()
    hello = {Atom("ok"): True, Atom("protocol"): 1, Atom("generation"): 0,
             Atom("backend"): {Atom("name"): backend, Atom("version"): "fault-fixture"},
             Atom("capabilities"): {}, Atom("pid"): os.getpid()}
    fault = mode.removeprefix("init-").removeprefix("query-")
    active = mode.startswith("init-") or log["packets"] > 1
    response = b"\x83" + etf(hello)
    if active:
        if fault == "hang":
            continue
        if fault == "exit":
            sys.exit(23)
        if fault == "refuse":
            hello.update({Atom("ok"): False, Atom("status"): Atom("error"), Atom("error"): "fixture refusal"})
            response = b"\x83" + etf(hello)
        elif fault == "identity":
            hello[Atom("backend")][Atom("name")] = "foreign-backend"
            response = b"\x83" + etf(hello)
        elif fault == "zero":
            response = b""
        elif fault == "oversized":
            response = b"\x83" + b"x" * 1048576
        elif fault == "bad-etf":
            response = b"\x83\xff"
        elif fault == "trailing":
            response += b"unconsumed"
        elif fault == "compressed":
            response = b"\x83\x50" + struct.pack(">I", len(response) - 1) + zlib.compress(response[1:])
        elif fault == "truncated":
            sys.stdout.buffer.write(struct.pack(">I", 100) + response[:2])
            sys.stdout.buffer.flush()
            sys.exit(23)
    sys.stdout.buffer.write(struct.pack(">I", len(response)) + response)
    sys.stdout.buffer.flush()
