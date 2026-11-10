"""Check all included original-term proofs and exact declared required coverage.

Fresh BL subject/bundle reconstruction supplies the model-plan connection.
This runner checks term leaves; it does not prove model-rule composition,
Source/compiler preservation, positive feasibility or receipt provenance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import term_refutation as terms

P = terms.P
require = terms.require


def typed_term_packet(packet):
    return {**packet, "profile": terms.k.Keyword(packet["profile"]), "semantics": terms.k.Keyword(packet["semantics"]),
            "identity-profile": terms.k.Keyword(packet["identity-profile"]),
            "assertions": [terms.typed_term(t) for t in packet["assertions"]], "claim": terms.typed_term(packet["claim"]),
            "normalized": terms.k.typed_packet(packet["normalized"])}


def canonical_identity(manifest):
    value = dict(manifest)
    for key in ["profile", "subject-kind", "model-connection", "composition", "feasibility", "kernel-execution", "identity-profile"]:
        value[key] = terms.k.Keyword(value[key])
    value["rows"] = []
    for row in manifest["rows"]:
        item = dict(row)
        for key in ["role", "mode", "status", "via"]:
            item[key] = terms.k.Keyword(item[key])
        if item["packet"] is not None:
            item["packet"] = typed_term_packet(item["packet"])
        value["rows"].append(item)
    del value["identity"]
    wire = b"\x83" + terms.k.etf(("bl/canonical-formal-data-v1", terms.normal(value)))
    require(len(wire) <= terms.k.MAX_BYTES, "obligation canonical byte capacity")
    return hashlib.sha256(wire).hexdigest()


FALSE_CLAIM = {"formal/term": 1, "sort": ["bool"], "op": "and", "data": None, "args": [
    {"formal/term": 1, "sort": ["bool"], "op": "bool", "args": [], "data": True},
    {"formal/term": 1, "sort": ["bool"], "op": "bool", "args": [], "data": False}]}


def digest(value, name):
    require(type(value) is str and terms.k.HEX.fullmatch(value), name + " identity digest")


def validate(manifest):
    require(type(manifest) is dict and set(manifest) == {"formal/obligation-term-manifest", "profile", "subject-kind", "subject", "plan", "rows", "model-connection", "composition", "feasibility", "kernel-execution", "compiler-proof-authority", "identity-profile", "identity"}, "obligation manifest fields")
    require(type(manifest["formal/obligation-term-manifest"]) is int and manifest["formal/obligation-term-manifest"] == 1, "obligation manifest version")
    require(manifest["profile"] == "bl/obligation-term-manifest-v1" and manifest["identity-profile"] == "bl/canonical-formal-data-v1", "obligation manifest profile")
    require(type(manifest["subject-kind"]) is str and manifest["subject-kind"] in {"query", "contract", "loop", "translation", "protocol", "source-protocol", "protocol-trace"}, "formal subject kind")
    require(manifest["model-connection"] == manifest["composition"] == "reviewed-not-mechanically-proved", "reviewed model/composition connection")
    require(manifest["feasibility"] == "not-established" and manifest["kernel-execution"] == "not-run", "export cannot assert execution/feasibility")
    require(manifest["compiler-proof-authority"] is False, "no compiler authority")
    for key in ["subject", "plan", "identity"]:
        digest(manifest[key], key)
    rows = manifest["rows"]
    require(type(rows) is list and 1 <= len(rows) <= 4096, "obligation row capacity")
    labels, required_count = set(), 0
    for row in rows:
        require(type(row) is dict and set(row) == {"label", "role", "required", "mode", "question", "unreachable", "status", "via", "packet", "diagnostic"}, "obligation evidence row fields")
        require(type(row["label"]) is str and row["label"] and row["label"] not in labels, "unique nonempty obligation label")
        labels.add(row["label"])
        require(type(row["required"]) is bool, "required coverage Boolean")
        required_count += int(row["required"])
        for key, allowed in [("role", {"property", "obligation", "witness", "inconsistency", "feasibility"}),
                             ("mode", {"sat", "prove"}), ("status", {"ready", "unknown", "unsupported", "error", "requires-witness"}),
                             ("via", {"entailment", "unreachable", "witness"})]:
            require(type(row[key]) is str and row[key] in allowed, "obligation " + key)
        require(row["required"] == (row["role"] in {"property", "obligation", "witness"}), "required role classification")
        require((row["mode"] == "sat") == (row["role"] in {"witness", "feasibility"}), "witness and proof modes remain distinct")
        require(row["diagnostic"] is None or type(row["diagnostic"]) is str, "text evidence diagnostic")
        digest(row["question"], "original obligation")
        if row["unreachable"] is not None:
            digest(row["unreachable"], "unreachable obligation")
        require((row["unreachable"] is not None) == (row["required"] and row["mode"] == "prove"), "unreachability route availability")
        if row["mode"] == "sat":
            require(row["status"] == "requires-witness" and row["via"] == "witness" and row["packet"] is None, "SAT witness cannot masquerade as checked refutation")
            continue
        require(row["status"] != "requires-witness" and row["via"] != "witness", "proof row route")
        if row["via"] == "unreachable":
            require(row["required"] and row["unreachable"] is not None, "only required properties can use unreachability")
        if row["status"] == "ready":
            require(row["diagnostic"] is None, "ready proof row has no failure diagnostic")
            terms.validate(row["packet"])
            target = row["unreachable"] if row["via"] == "unreachable" else row["question"]
            require(row["packet"]["normalized"]["question"] == target, "proof packet belongs to another obligation target")
            if row["via"] == "unreachable" or row["role"] == "inconsistency":
                require(row["packet"]["claim"] == FALSE_CLAIM, "inconsistency/unreachability must prove the explicit false goal")
        else:
            require(row["packet"] is None, "pending row cannot carry a proof packet")
    require(required_count > 0, "empty required coverage cannot establish a model promise")
    require(canonical_identity(manifest) == manifest["identity"], "obligation manifest canonical identity mismatch")


def run(path, output):
    require(path.stat().st_size <= terms.k.MAX_BYTES, "obligation manifest byte capacity")
    manifest = terms.k.load_packet(path)
    validate(manifest)
    output.mkdir(parents=True, exist_ok=True)
    checked, pending, required, ready_required, unreachable = [], [], 0, 0, 0
    inconsistent = False
    for index, row in enumerate(manifest["rows"]):
        if row["required"]:
            required += 1
        if row["status"] != "ready":
            if row["required"]:
                pending.append({"label": row["label"], "status": row["status"], "role": row["role"]})
            continue
        target = output / "rows" / f"{index:04d}"
        target.mkdir(parents=True, exist_ok=True)
        packet = target / "packet.json"
        packet.write_text(json.dumps(row["packet"]) + "\n")
        receipt = terms.run(packet, target)
        if row["required"]:
            ready_required += 1
            unreachable += int(row["via"] == "unreachable")
        inconsistent = inconsistent or row["role"] == "inconsistency"
        checked.append({"index": index, "label": row["label"], "role": row["role"], "required": row["required"], "via": row["via"],
                        "packet": row["packet"]["identity"], "proof_source_sha256": receipt["proof_source_sha256"],
                        "proof_olean_sha256": receipt["proof_olean_sha256"], "axioms": receipt["axioms"]})
    result = {"schema": "enchant.formal.obligation-term-execution.v1",
              "status": "checked-required-term-evidence" if not pending else "incomplete-obligation-evidence",
              "manifest": manifest["identity"], "subject_kind": manifest["subject-kind"], "subject": manifest["subject"], "plan": manifest["plan"],
              "coverage": {"required": required, "ready": ready_required, "unreachable": unreachable, "complete": not pending},
              "checked": checked, "pending": pending,
              "initial_assumption_consistency": "inconsistent-in-contained-typed-term-model" if inconsistent else "not-established",
              "positive_feasibility": "not-established", "scope": "checked-stated-term-leaves-and-required-coverage",
              "model_connection": "requires-fresh-BL-subject-plan-reconstruction", "model_composition": "reviewed-not-mechanically-proved",
              "model_theorem": "not-established-by-this-runner", "source_runtime_refinement": "not-established",
              "runtime_attestation": "local-checker-observation-not-cryptographic-attestation", "compiler_proof_authority": False}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.manifest, args.output)
        print(json.dumps({"status": result["status"], "coverage": result["coverage"], "compiler_proof_authority": False}))
        if not result["coverage"]["complete"]:
            raise SystemExit(2)
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        args.output.mkdir(parents=True, exist_ok=True)
        result = {"status": "not-accepted", "reason": str(error), "compiler_proof_authority": False}
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result)); raise SystemExit(1)


if __name__ == "__main__":
    main()
