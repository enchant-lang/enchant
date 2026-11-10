"""Execute the pinned sound normalized checker on a BL-exported data packet.

The canonical packet identity and generated Lean data are independently decoded
and compared. This does not prove BL term normalization or this data bridge.
Only fixed constructor names, Booleans and validated integers enter Lean source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parent
MAX_BYTES = 8 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}\Z")


class Keyword(str):
    pass


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def etf(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    if isinstance(value, bytes):
        return b"m" + len(value).to_bytes(4, "big") + value
    if type(value) is int:
        if 0 <= value <= 255:
            return b"a" + bytes([value])
        if -(2**31) <= value < 2**31:
            return b"b" + value.to_bytes(4, "big", signed=True)
        size = (abs(value).bit_length() + 7) // 8
        prefix = b"n" + bytes([size]) if size < 256 else b"o" + size.to_bytes(4, "big")
        return prefix + bytes([int(value < 0)]) + abs(value).to_bytes(size, "little")
    if isinstance(value, tuple):
        require(len(value) < 256, "ETF tuple capacity")
        return b"h" + bytes([len(value)]) + b"".join(map(etf, value))
    if isinstance(value, list):
        return b"j" if not value else b"l" + len(value).to_bytes(4, "big") + b"".join(map(etf, value)) + b"j"
    raise ValueError("unmodeled ETF normal-form value")


def normal(value):
    if isinstance(value, Keyword):
        return ("keyword", str(value))
    if type(value) is bool:
        return ("bool", int(value))
    if type(value) is int:
        return ("int", value)
    if isinstance(value, str):
        return ("binary", value)
    if isinstance(value, list):
        return ("vector", [normal(v) for v in value])
    if isinstance(value, dict):
        entries = [(normal(Keyword(k)), normal(v)) for k, v in value.items()]
        return ("map", sorted(entries, key=lambda pair: etf(pair[0])))
    raise ValueError("unmodeled canonical packet value")


def typed_packet(packet):
    """Recover the public BL kinds lost by this deliberately narrow JSON view."""
    value = dict(packet)
    for name in ["profile", "rules", "identity-profile"]:
        value[name] = Keyword(value[name])

    def formula(node):
        return [Keyword(node[0]), *[formula(v) if isinstance(v, list) else v for v in node[1:]]]

    def proof(node):
        if node[0] == "split":
            return [Keyword("split"), node[1], proof(node[2]), proof(node[3])]
        return [Keyword(node[0]), *node[1:]]

    value["kernel"] = {
        "atoms": [[Keyword(a[0]), *a[1:]] for a in packet["kernel"]["atoms"]],
        "formulas": [formula(f) for f in packet["kernel"]["formulas"]],
        "proof": proof(packet["kernel"]["proof"]),
    }
    return value


def canonical_identity(packet):
    value = typed_packet(packet)
    del value["identity"]
    wire = b"\x83" + etf(("bl/canonical-formal-data-v1", normal(value)))
    require(len(wire) <= MAX_BYTES, "canonical packet byte capacity")
    return hashlib.sha256(wire).hexdigest()


def load_packet(path):
    def distinct_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON object key")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=distinct_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON number")))


def integer(value):
    require(type(value) is int, "integer required, Boolean is not an integer")


def validate(packet):
    fields = {"formal/normalized-refutation", "profile", "rules", "statement", "question", "variables", "booleans", "kernel", "identity-profile", "identity"}
    require(type(packet) is dict and set(packet) == fields, "packet fields")
    require(packet["formal/normalized-refutation"] == 1 and type(packet["formal/normalized-refutation"]) is int, "packet version")
    require(packet["profile"] == "bl/normalized-refutation-v1", "packet profile")
    require(packet["identity-profile"] == "bl/canonical-formal-data-v1", "identity profile")
    require(packet["rules"] in {"bl/boolean-linear-integer-v1", "bl/boolean-piecewise-linear-integer-v2", "bl/piecewise-ground-integer-v3"}, "rule system")
    for key in ["statement", "question", "identity"]:
        require(type(packet[key]) is str and HEX.fullmatch(packet[key]), key + " digest")
    variables = packet["variables"]
    require(type(variables) is list and len(variables) <= 1024 and all(type(v) is str for v in variables) and len(set(variables)) == len(variables), "distinct integer names")
    kernel = packet["kernel"]
    require(type(kernel) is dict and set(kernel) == {"atoms", "formulas", "proof"}, "kernel fields")
    require(type(kernel["atoms"]) is list and len(kernel["atoms"]) <= 32, "atom capacity")
    boolean_ids = []
    for index, atom in enumerate(kernel["atoms"]):
        require(type(atom) is list and atom, "atom shape")
        if atom[0] == "boolean":
            require(len(atom) == 1, "Boolean atom shape")
            boolean_ids.append(index)
        else:
            require(atom[0] == "linear" and len(atom) == 3 and type(atom[1]) is list and len(atom[1]) == len(variables), "linear atom shape")
            for value in [*atom[1], atom[2]]:
                integer(value)
            import math
            require(math.gcd(*atom[1]) == 1, "primitive normalized coefficient vector")
    names = packet["booleans"]
    require(type(names) is list and all(type(n) is list and len(n) == 2 and type(n[0]) is int and type(n[1]) is str for n in names), "Boolean names")
    require([n[0] for n in names] == boolean_ids and len({n[1] for n in names}) == len(names), "exact Boolean atom name map")
    visits = 0

    def formula(node, depth=0):
        nonlocal visits
        visits += 1
        require(visits <= 65536 and depth <= 128 and type(node) is list and node, "formula capacity/shape")
        tag = node[0]
        if tag == "constant":
            require(len(node) == 2 and type(node[1]) is bool, "Boolean constant")
        elif tag == "atom":
            require(len(node) == 2 and type(node[1]) is int and 0 <= node[1] < len(kernel["atoms"]), "formula atom index")
        elif tag == "neg":
            require(len(node) == 2, "negation arity")
            formula(node[1], depth + 1)
        else:
            require(tag in {"both", "either"} and len(node) == 3, "Boolean connective")
            formula(node[1], depth + 1)
            formula(node[2], depth + 1)

    require(type(kernel["formulas"]) is list and 1 <= len(kernel["formulas"]) <= 4096, "formula list")
    for item in kernel["formulas"]:
        formula(item)
    nodes = 0

    def proof(node, depth=0):
        nonlocal nodes
        nodes += 1
        require(nodes <= 8192 and depth <= 64 and type(node) is list and node, "proof capacity/shape")
        tag = node[0]
        if tag == "boolean":
            require(len(node) == 1, "Boolean proof shape")
        elif tag == "split":
            require(len(node) == 4 and type(node[1]) is int and 0 <= node[1] < len(kernel["atoms"]), "split index/arity")
            proof(node[2], depth + 1)
            proof(node[3], depth + 1)
        else:
            require(tag == "linear" and len(node) == 2 and type(node[1]) is list and 1 <= len(node[1]) <= 32, "linear proof shape")
            for weight in node[1]:
                require(type(weight) is list and len(weight) == 2, "weight entry")
                require(type(weight[0]) is int and 0 <= weight[0] < len(kernel["atoms"]), "weight atom index")
                require(type(weight[1]) is int and 0 < weight[1] < 2**4096, "positive bounded weight")
    proof(kernel["proof"])
    require(canonical_identity(packet) == packet["identity"], "packet canonical identity mismatch")


def emit_list(values):
    return "[" + ", ".join(values) + "]"


def emit_int(value):
    return f"(Int.ofNat {value})" if value >= 0 else f"(Int.negSucc {-value - 1})"


def emit_formula(node):
    tag = node[0]
    if tag == "constant":
        return "(Formula.constant " + str(node[1]).lower() + ")"
    if tag == "atom":
        return f"(Formula.atom {node[1]})"
    if tag == "neg":
        return "(Formula.neg " + emit_formula(node[1]) + ")"
    return f"(Formula.{tag} {emit_formula(node[1])} {emit_formula(node[2])})"


def emit_atom(node):
    if node[0] == "boolean":
        return "Atom.boolean"
    return "(Atom.linear (Row.mk " + emit_list([emit_int(v) for v in node[1]]) + " " + emit_int(node[2]) + "))"


def emit_proof(node):
    if node[0] == "boolean":
        return "Proof.boolean"
    if node[0] == "split":
        return f"(Proof.split {node[1]} {emit_proof(node[2])} {emit_proof(node[3])})"
    return "(Proof.linear " + emit_list([f"({i}, {w})" for i, w in node[1]]) + ")"


HEADER = "import Refutation\nset_option maxRecDepth 100000\nset_option maxHeartbeats 20000000\nopen FormalRefutation\n\ndef packetProblem : Problem :=\n"
BETWEEN = "\n\ndef packetProof : Proof :=\n"
TAIL = "\n\ntheorem packetAccepted : check packetProblem packetProof = true := by decide\ntheorem packetUnsatisfiable : ∀ integers booleans, ¬ packetProblem.satisfied integers booleans :=\n  checked_refutation_unsatisfiable packetProblem packetProof packetAccepted\n#print axioms packetAccepted\n#print axioms packetUnsatisfiable\n"


def source(kernel):
    problem = "(Problem.mk " + emit_list([emit_atom(a) for a in kernel["atoms"]]) + " " + emit_list([emit_formula(f) for f in kernel["formulas"]]) + ")"
    return HEADER + problem + BETWEEN + emit_proof(kernel["proof"]) + TAIL


class Decoder:
    """A distinct small parser; does not invoke the Lean-source emitter."""
    def __init__(self, text):
        self.tokens = re.findall(r"[A-Za-z][A-Za-z.]*|[0-9]+|[()[\],]", text)
        require("".join(self.tokens) == re.sub(r"\s+", "", text), "unknown generated source token")
        self.at = 0

    def take(self, expected=None):
        require(self.at < len(self.tokens), "incomplete generated data")
        value = self.tokens[self.at]
        self.at += 1
        require(expected is None or value == expected, "unexpected generated token")
        return value

    def nat(self):
        token = self.take()
        require(token.isdecimal(), "generated natural numeral")
        return int(token)

    def list(self, parser):
        self.take("[")
        result = []
        if self.tokens[self.at] != "]":
            result.append(parser())
            while self.tokens[self.at] == ",":
                self.take(",")
                result.append(parser())
        self.take("]")
        return result

    def int(self):
        self.take("(")
        ctor = self.take()
        require(ctor in {"Int.ofNat", "Int.negSucc"}, "generated integer constructor")
        value = self.nat()
        self.take(")")
        return value if ctor == "Int.ofNat" else -value - 1

    def atom(self):
        if self.tokens[self.at] == "Atom.boolean":
            self.take()
            return ["boolean"]
        self.take("("); self.take("Atom.linear"); self.take("("); self.take("Row.mk")
        coefficients = self.list(self.int)
        bound = self.int()
        self.take(")"); self.take(")")
        return ["linear", coefficients, bound]

    def formula(self):
        self.take("(")
        ctor = self.take()
        if ctor == "Formula.constant":
            value = self.take(); require(value in {"true", "false"}, "generated Boolean")
            result = ["constant", value == "true"]
        elif ctor == "Formula.atom":
            result = ["atom", self.nat()]
        elif ctor == "Formula.neg":
            result = ["neg", self.formula()]
        else:
            require(ctor in {"Formula.both", "Formula.either"}, "generated formula constructor")
            result = [ctor.split(".")[1], self.formula(), self.formula()]
        self.take(")")
        return result

    def proof(self):
        if self.tokens[self.at] == "Proof.boolean":
            self.take()
            return ["boolean"]
        self.take("(")
        ctor = self.take()
        if ctor == "Proof.split":
            result = ["split", self.nat(), self.proof(), self.proof()]
        else:
            require(ctor == "Proof.linear", "generated proof constructor")
            def weight():
                self.take("("); index = self.nat(); self.take(","); value = self.nat(); self.take(")")
                return [index, value]
            result = ["linear", self.list(weight)]
        self.take(")")
        return result


def verify_source(text, kernel):
    require(text.startswith(HEADER) and text.endswith(TAIL), "generated source template")
    data = text[len(HEADER):-len(TAIL)]
    require(data.count(BETWEEN) == 1, "generated data boundaries")
    problem, proof = data.split(BETWEEN)
    parser = Decoder(problem)
    parser.take("("); parser.take("Problem.mk")
    atoms, formulas = parser.list(parser.atom), parser.list(parser.formula)
    parser.take(")"); require(parser.at == len(parser.tokens), "trailing problem data")
    parser = Decoder(proof)
    tree = parser.proof(); require(parser.at == len(parser.tokens), "trailing proof data")
    require({"atoms": atoms, "formulas": formulas, "proof": tree} == kernel, "generated Lean data differs from packet")


def run(packet_path, output):
    require(packet_path.stat().st_size <= MAX_BYTES, "packet byte capacity")
    packet = load_packet(packet_path)
    validate(packet)
    text = source(packet["kernel"])
    verify_source(text, packet["kernel"])
    pin = json.loads((PROJECT / "metatheory/refutation-pin.json").read_text())
    tool = json.loads((PROJECT / "metatheory/tool-pin.json").read_text())
    lean = Path(tool["path"]) / "bin/lean"
    require(sha(lean) == tool["binary_sha256"], "Lean executable pin")
    artifact = PROJECT / pin["compiled"]["path"]
    require(sha(artifact) == pin["compiled"]["sha256"], "compiled kernel pin")
    require(sha(PROJECT / pin["source"]["path"]) == pin["source"]["sha256"], "kernel source pin")
    output.mkdir(parents=True, exist_ok=True)
    (output / "Check.lean").write_text(text)
    with tempfile.TemporaryDirectory(prefix="enchant-refutation-") as work:
        work = Path(work)
        library = work / "library"; library.mkdir()
        shutil.copyfile(artifact, library / "Refutation.olean")
        path = work / "Check.lean"; path.write_text(text)
        env = dict(os.environ, LEAN_PATH=str(library))
        completed = subprocess.run([str(lean), "--root=" + str(work), "-o", str(work / "Check.olean"), str(path)],
                                   cwd=work, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (output / "lean.txt").write_text(completed.stdout)
        require(completed.returncode == 0 and "sorryAx" not in completed.stdout and "warning:" not in completed.stdout, "Lean did not accept the normalized refutation")
        audits = {}
        for line in completed.stdout.splitlines():
            match = re.fullmatch(r"'([^']+)' (?:does not depend on any axioms|depends on axioms: \[(.*)\])", line)
            require(match is not None, "unexpected Lean audit output")
            audits[match[1]] = match[2].split(", ") if match[2] else []
        require(audits == {"packetAccepted": ["propext"], "packetUnsatisfiable": ["propext", "Quot.sound"]}, "unexpected theorem/axiom dependencies")
        shutil.copyfile(work / "Check.olean", output / "Check.olean")
    result = {"schema": "enchant.formal.normalized-refutation-execution.v1", "status": "checked-normalized-refutation",
              "packet": packet["identity"], "statement": packet["statement"], "question": packet["question"],
              "kernel_source_sha256": pin["source"]["sha256"], "kernel_olean_sha256": pin["compiled"]["sha256"],
              "proof_source_sha256": sha(output / "Check.lean"), "proof_olean_sha256": sha(output / "Check.olean"),
              "axioms": audits, "canonical_packet_identity": "independently-recomputed",
              "source_data": "independently-decoded-and-compared", "data_bridge_soundness": "reviewed-not-mechanically-proved",
              "term_normalization": "reviewed-not-mechanically-proved", "source_compiler_preservation": "not-established",
              "runtime_attestation": "local-checker-observation-not-cryptographic-attestation", "compiler_proof_authority": False}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args.packet, args.output)
        print(json.dumps({"status": result["status"], "packet": result["packet"], "compiler_proof_authority": False}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError) as error:
        args.output.mkdir(parents=True, exist_ok=True)
        result = {"status": "not-accepted", "reason": str(error), "compiler_proof_authority": False}
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
