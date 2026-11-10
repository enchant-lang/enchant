"""Check original typed term entailment through a per-question connection proof.

BL's normalizer is not trusted: Lean checks countermodel preservation for these
original trees before applying the sound normalized refutation theorem.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import refutation_kernel as k

P = k.PROJECT
require = k.require


def normal(value):
    if value is None:
        return ("nil",)
    if isinstance(value, dict):
        return ("map", sorted([(normal(k.Keyword(key)), normal(v)) for key, v in value.items()], key=lambda pair: k.etf(pair[0])))
    if isinstance(value, list):
        return ("vector", [normal(v) for v in value])
    return k.normal(value)


def typed_term(term):
    return {**term, "op": k.Keyword(term["op"]), "sort": [k.Keyword(term["sort"][0])],
            "args": [typed_term(child) for child in term["args"]]}


def guards(packet):
    result, seen = [], set()
    def visit(node):
        for child in node["args"]:
            visit(child)
        if node["op"] == "ite":
            condition = node["args"][0]
            key = json.dumps(condition, sort_keys=True)
            if key not in seen:
                seen.add(key); result.append(condition)
    for root in [*packet["assertions"], packet["claim"]]:
        visit(root)
    return result


def canonical_identity(packet):
    value = {**packet, "profile": k.Keyword(packet["profile"]), "semantics": k.Keyword(packet["semantics"]),
             "identity-profile": k.Keyword(packet["identity-profile"]),
             "assertions": [typed_term(t) for t in packet["assertions"]], "claim": typed_term(packet["claim"]),
             "normalized": k.typed_packet(packet["normalized"])}
    del value["identity"]
    wire = b"\x83" + k.etf(("bl/canonical-formal-data-v1", normal(value)))
    require(len(wire) <= k.MAX_BYTES, "canonical term packet capacity")
    import hashlib
    return hashlib.sha256(wire).hexdigest()


def validate_roots(roots):
    """Validate the shared partial Int/Bool grammar, without proof case limits."""
    variables, visits = {}, 0

    def term(node, depth=0):
        nonlocal visits
        visits += 1
        require(visits <= 65536 and depth <= 128, "original term capacity")
        require(type(node) is dict and set(node) == {"formal/term", "sort", "op", "args", "data"}, "original term fields")
        require(type(node["formal/term"]) is int and node["formal/term"] == 1, "original term version")
        require(node["sort"] in [["int"], ["bool"]], "original term sort")
        sort, op, args, data = node["sort"][0], node["op"], node["args"], node["data"]
        require(type(op) is str and type(args) is list, "original operation/arguments")
        if op in {"int", "bool", "var"}:
            require(not args, "literal/input arity")
            if op == "int":
                require(sort == "int" and type(data) is int, "integer literal")
            elif op == "bool":
                require(sort == "bool" and type(data) is bool, "Boolean literal")
            else:
                require(type(data) is str and data and "\0" not in data, "input name")
                require(data not in variables or variables[data] == sort, "input sort conflict")
                variables[data] = sort
            return sort
        require(data is None, "operation payload outside this term encoding")
        children = [term(child, depth + 1) for child in args]
        if op in {"add", "sub", "mul", "div", "mod"}:
            require(sort == "int" and children == ["int", "int"], "integer operation")
        elif op == "neg":
            require(sort == "int" and children == ["int"], "integer negation")
        elif op in {"le", "lt", "ge", "gt"}:
            require(sort == "bool" and children == ["int", "int"], "integer relation")
        elif op == "eq":
            require(sort == "bool" and len(children) == 2 and children[0] == children[1], "typed equality")
        elif op == "not":
            require(sort == "bool" and children == ["bool"], "Boolean negation")
        elif op in {"implies", "xor"}:
            require(sort == "bool" and children == ["bool", "bool"], "binary Boolean operation")
        elif op in {"and", "or"}:
            require(sort == "bool" and all(s == "bool" for s in children), "variadic Boolean operation")
        else:
            require(op == "ite" and children == ["bool", sort, sort], "typed choice or unsupported operation")
        return sort

    require(type(roots) is list and len(roots) <= 4097, "original root list")
    for root in roots:
        require(term(root) == "bool", "original question roots must be Boolean")
    return variables


def validate(packet):
    require(type(packet) is dict and set(packet) == {"formal/term-refutation", "profile", "semantics", "assertions", "claim", "normalized", "identity-profile", "identity"}, "term packet fields")
    require(type(packet["formal/term-refutation"]) is int and packet["formal/term-refutation"] == 1, "term packet version")
    require(packet["profile"] == "bl/typed-term-refutation-v1" and packet["semantics"] == "bl/partial-mathematical-int-bool-v1", "term profile/semantics")
    require(packet["identity-profile"] == "bl/canonical-formal-data-v1", "term identity profile")
    require(type(packet["identity"]) is str and k.HEX.fullmatch(packet["identity"]), "term packet digest")
    k.validate(packet["normalized"])
    require(type(packet["assertions"]) is list and len(packet["assertions"]) <= 4096, "original assertion list")
    variables = validate_roots([*packet["assertions"], packet["claim"]])
    integers = sorted(name for name, sort in variables.items() if sort == "int")
    booleans = sorted(name for name, sort in variables.items() if sort == "bool")
    require(len(integers) <= 1024 and len(booleans) <= 12, "original input/Boolean case proof capacity")
    require(len(booleans) + len(guards(packet)) <= 12, "original Boolean/choice case proof capacity")
    normalized = packet["normalized"]
    require(all(name in integers for name in normalized["variables"]), "normalized integer name is not an original input")
    require(all(name in booleans for _, name in normalized["booleans"]), "normalized Boolean name is not an original input")
    require(canonical_identity(packet) == packet["identity"], "original term canonical identity mismatch")
    return integers, booleans


def emit_term(node, integers, booleans):
    op, args = node["op"], node["args"]
    if op == "int":
        return "(Term.int " + k.emit_int(node["data"]) + ")"
    if op == "bool":
        return "(Term.bool " + str(node["data"]).lower() + ")"
    if op == "var":
        names = integers if node["sort"] == ["int"] else booleans
        return "(Term.input" + ("Int" if node["sort"] == ["int"] else "Bool") + " " + str(names.index(node["data"])) + ")"
    if op in {"and", "or"}:
        result = "(Term.bool " + ("true" if op == "and" else "false") + ")"
        for child in reversed(args):
            result = "(Term." + op + " " + emit_term(child, integers, booleans) + " " + result + ")"
        return result
    if op in {"ge", "gt"}:
        op, args = ("le" if op == "ge" else "lt"), list(reversed(args))
    elif op == "eq":
        op = "eqInt" if args[0]["sort"] == ["int"] else "eqBool"
    return "(Term." + op + " " + " ".join(emit_term(a, integers, booleans) for a in args) + ")"


class TermDecoder(k.Decoder):
    def term(self):
        self.take("(")
        tag = self.take()
        require(tag.startswith("Term."), "generated term constructor")
        op = tag[5:]
        if op == "int":
            result = [op, self.int()]
        elif op == "bool":
            value = self.take(); require(value in {"true", "false"}, "generated term Boolean")
            result = [op, value == "true"]
        elif op in {"inputInt", "inputBool"}:
            result = [op, self.nat()]
        else:
            require(op in {"add", "sub", "mul", "div", "mod", "neg", "le", "lt", "eqInt", "eqBool", "not", "and", "or", "implies", "xor", "ite"}, "generated term operation")
            arity = 1 if op in {"neg", "not"} else 3 if op == "ite" else 2
            result = [op, *[self.term() for _ in range(arity)]]
        self.take(")")
        return result


def faithful(node, ast, integers, booleans):
    """Check a decoded AST against original terms without invoking the emitter."""
    op, args = node["op"], node["args"]
    if op in {"int", "bool"}:
        return ast == [op, node["data"]]
    if op == "var":
        names = integers if node["sort"] == ["int"] else booleans
        tag = "inputInt" if node["sort"] == ["int"] else "inputBool"
        return len(ast) == 2 and ast[0] == tag and 0 <= ast[1] < len(names) and names[ast[1]] == node["data"]
    if op in {"and", "or"}:
        for child in args:
            if len(ast) != 3 or ast[0] != op or not faithful(child, ast[1], integers, booleans):
                return False
            ast = ast[2]
        return ast == ["bool", op == "and"]
    if op in {"ge", "gt"}:
        return len(ast) == 3 and ast[0] == ("le" if op == "ge" else "lt") and faithful(args[1], ast[1], integers, booleans) and faithful(args[0], ast[2], integers, booleans)
    tag = ("eqInt" if args[0]["sort"] == ["int"] else "eqBool") if op == "eq" else op
    return len(ast) == len(args) + 1 and ast[0] == tag and all(faithful(child, decoded, integers, booleans) for child, decoded in zip(args, ast[1:]))


HEADER = "import Terms\nset_option maxRecDepth 5000\nset_option maxHeartbeats 2000000\nset_option linter.unusedSimpArgs false\nopen FormalRefutation FormalTerms\n\ndef originalQuestion : Question :=\n"
PROBLEM = "\n\ndef packetProblem : Problem :=\n"
PROOF = "\n\ndef packetProof : Proof :=\n"
MAP_I = "\n\ndef integerMap (integers : Nat → Int) (index : Nat) : Int := integers (("
MAP_B = "\n\ndef booleanMap (booleans : Nat → Bool) (index : Nat) : Bool := booleans (("
MAP_END = " : List Nat)[index]?.getD 0)"
SIMPS = "Term.eval, strict₂, partial₂, divide, modulus"


def tail(packet, integers, booleans):
    cases = "".join(f"  all_goals cases h{index} : booleans {index}\n" for index in range(len(booleans)))
    for index, condition in enumerate(guards(packet)):
        expression = emit_term(condition, integers, booleans)
        cases += f"  all_goals cases hGuard{index} : {expression}.eval integers booleans\n"
        cases += f"  all_goals first | (rename_i guardValue{index}; cases guardValue{index}) | skip\n"
        cases += f"  all_goals simp only [{SIMPS}, known_and, known_or, known_not, FormalTerms.false_and, FormalTerms.and_false, FormalTerms.true_or, FormalTerms.or_true] at *\n"
        cases += f"  all_goals try simp only [hGuard{index}] at failed\n"
        cases += f"  all_goals try simp only [hGuard{index}] at assumed\n"
    return """

theorem packetAccepted : check packetProblem packetProof = true := by decide
theorem normalizationConnected : ∀ integers booleans,
    originalQuestion.assumed integers booleans →
    originalQuestion.claim.eval integers booleans ≠ some true →
    packetProblem.satisfied (integerMap integers) (booleanMap booleans) := by
  intro integers booleans assumed failed
  all_goals simp [Question.assumed, originalQuestion] at assumed
  all_goals simp only [originalQuestion] at failed
  all_goals simp only [Problem.satisfied, packetProblem]
  all_goals simp only [List.mem_cons, List.not_mem_nil, forall_eq_or_imp, forall_eq, forall_false, implies_true, and_true]
  all_goals try dsimp only [Formula.eval]
  all_goals try dsimp only [Problem.values]
  all_goals simp only [List.getElem?_cons_zero, List.getElem?_cons_succ, List.getElem?_nil]
  all_goals simp [Row.holds, dot, integerMap, booleanMap]
""" + cases + f"  all_goals simp_all [{SIMPS}]\n  all_goals try dsimp (config := {{ instances := true }}) only [Ty.Value] at *\n  all_goals omega\n" + """
theorem originalQuestionEntails : originalQuestion.entails :=
  connected_refutation_entails originalQuestion packetProblem packetProof integerMap booleanMap normalizationConnected packetAccepted
#print axioms packetAccepted
#print axioms normalizationConnected
#print axioms originalQuestionEntails
"""


def mappings(packet, integers, booleans):
    normalized = packet["normalized"]
    i = [integers.index(name) for name in normalized["variables"]]
    names = dict(normalized["booleans"])
    b = [booleans.index(names[index]) if index in names else 0 for index in range(len(normalized["kernel"]["atoms"]))]
    return i, b


def source(packet, integers, booleans):
    terms = lambda node: emit_term(node, integers, booleans)
    question = "(Question.mk " + k.emit_list([terms(t) for t in packet["assertions"]]) + " " + terms(packet["claim"]) + ")"
    kernel = packet["normalized"]["kernel"]
    problem = "(Problem.mk " + k.emit_list([k.emit_atom(a) for a in kernel["atoms"]]) + " " + k.emit_list([k.emit_formula(f) for f in kernel["formulas"]]) + ")"
    i, b = mappings(packet, integers, booleans)
    return HEADER + question + PROBLEM + problem + PROOF + k.emit_proof(kernel["proof"]) + MAP_I + k.emit_list(list(map(str, i))) + MAP_END + MAP_B + k.emit_list(list(map(str, b))) + MAP_END + tail(packet, integers, booleans)


def verify_source(text, packet, integers, booleans):
    ending = tail(packet, integers, booleans)
    require(text.startswith(HEADER) and text.endswith(ending), "original proof source template")
    question, rest = text[len(HEADER):-len(ending)].split(PROBLEM)
    problem, rest = rest.split(PROOF)
    proof, rest = rest.split(MAP_I)
    i, b = rest.split(MAP_B)
    p = TermDecoder(question)
    p.take("("); p.take("Question.mk")
    assertions, claim = p.list(p.term), p.term()
    p.take(")"); require(p.at == len(p.tokens), "trailing original question data")
    require(len(assertions) == len(packet["assertions"]) and all(faithful(t, ast, integers, booleans) for t, ast in zip(packet["assertions"], assertions)) and faithful(packet["claim"], claim, integers, booleans), "generated original terms differ from packet")
    p = k.Decoder(problem); p.take("("); p.take("Problem.mk")
    atoms, formulas = p.list(p.atom), p.list(p.formula)
    p.take(")"); require(p.at == len(p.tokens), "trailing normalized problem data")
    p = k.Decoder(proof); tree = p.proof(); require(p.at == len(p.tokens), "trailing normalized proof data")
    require({"atoms": atoms, "formulas": formulas, "proof": tree} == packet["normalized"]["kernel"], "generated normalized data differs from packet")
    recovered = []
    for data in [i, b]:
        require(data.endswith(MAP_END), "generated variable mapping template")
        p = k.Decoder(data[:-len(MAP_END)])
        recovered.append(p.list(p.nat)); require(p.at == len(p.tokens), "trailing mapping data")
    require(tuple(recovered) == mappings(packet, integers, booleans), "variable mappings differ from original names")


AXIOM_POLICIES = {"choice-free": {"propext", "Quot.sound"},
                  "lean-standard": {"propext", "Classical.choice", "Quot.sound"}}


def run(path, output, axiom_policy="choice-free"):
    require(axiom_policy in AXIOM_POLICIES, "unknown axiom policy")
    require(path.stat().st_size <= k.MAX_BYTES, "term packet byte capacity")
    packet = k.load_packet(path)
    integers, booleans = validate(packet)
    text = source(packet, integers, booleans)
    verify_source(text, packet, integers, booleans)
    tool = json.loads((P / "metatheory/tool-pin.json").read_text())
    lean = Path(tool["path"]) / "bin/lean"
    require(k.sha(lean) == tool["binary_sha256"], "Lean executable pin")
    pins = [json.loads((P / name).read_text()) for name in ["metatheory/refutation-pin.json", "metatheory/terms-pin.json"]]
    require(k.sha(P / "metatheory/refutation-pin.json") == pins[1]["normalized_kernel_pin_sha256"], "term model normalized dependency pin")
    for pin in pins:
        for key in ["source", "compiled"]:
            require(k.sha(P / pin[key]["path"]) == pin[key]["sha256"], "term/kernel artifact pin")
    output.mkdir(parents=True, exist_ok=True)
    (output / "Check.lean").write_text(text)
    # A new failed invocation must never leave an earlier compiled success.
    (output / "Check.olean").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="enchant-terms-") as temporary:
        work = Path(temporary); library = work / "library"; library.mkdir()
        for pin, module in zip(pins, ["Refutation", "Terms"]):
            shutil.copyfile(P / pin["compiled"]["path"], library / (module + ".olean"))
        check = work / "Check.lean"; check.write_text(text)
        with (output / "lean.txt").open("w") as log:
            completed = subprocess.run([str(lean), "--root=" + str(work), "-o", str(work / "Check.olean"), str(check)], cwd=work,
                                       env=dict(os.environ, LEAN_PATH=str(library)), text=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        transcript = (output / "lean.txt").read_text()
        require(completed.returncode == 0 and "sorryAx" not in transcript and "warning:" not in transcript, "Lean did not accept original-term connection/refutation")
        import re
        audits = {}
        for line in transcript.splitlines():
            match = re.fullmatch(r"'([^']+)' (?:does not depend on any axioms|depends on axioms: \[(.*)\])", line)
            require(match is not None, "unexpected term theorem audit")
            audits[match[1]] = match[2].split(", ") if match[2] else []
        require(set(audits) == {"packetAccepted", "normalizationConnected", "originalQuestionEntails"}, "term theorem audit names")
        connection_axioms = set(audits["normalizationConnected"])
        final_axioms = set(audits["originalQuestionEntails"])
        require(audits["packetAccepted"] == ["propext"] and connection_axioms <= AXIOM_POLICIES[axiom_policy]
                and final_axioms == {"propext", "Quot.sound"} | connection_axioms, "term theorem axiom dependencies exceed policy")
        shutil.copyfile(work / "Check.olean", output / "Check.olean")
    result = {"schema": "enchant.formal.typed-term-refutation-execution.v1", "status": "checked-term-entailment",
              "packet": packet["identity"], "normalized_packet": packet["normalized"]["identity"], "question": packet["normalized"]["question"],
              "semantics": packet["semantics"], "proof_source_sha256": k.sha(output / "Check.lean"), "proof_olean_sha256": k.sha(output / "Check.olean"),
              "term_model_source_sha256": pins[1]["source"]["sha256"], "term_model_olean_sha256": pins[1]["compiled"]["sha256"],
              "axioms": audits, "axiom_policy": axiom_policy, "allowed_axioms": sorted(AXIOM_POLICIES[axiom_policy]),
              "canonical_packet_identity": "independently-recomputed", "source_data": "independently-decoded-and-compared",
              "normalization_connection": "checked-countermodel-preservation-for-this-question", "general_bl_normalizer_soundness": "not-established",
              "term_data_model_correspondence": "reviewed-data-semantics-bridge", "source_compiler_preservation": "not-established",
              "runtime_attestation": "local-checker-observation-not-cryptographic-attestation", "compiler_proof_authority": False}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--axiom-policy", choices=sorted(AXIOM_POLICIES), default="choice-free")
    args = parser.parse_args()
    try:
        result = run(args.packet, args.output, args.axiom_policy)
        print(json.dumps({"status": result["status"], "packet": result["packet"], "compiler_proof_authority": False}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        args.output.mkdir(parents=True, exist_ok=True)
        result = {"status": "not-accepted", "reason": str(error), "compiler_proof_authority": False}
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result)); raise SystemExit(1)


if __name__ == "__main__":
    main()
