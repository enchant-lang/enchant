"""Real original-term proofs and adversarial semantic/data connections, sequential."""
import copy
import json
from pathlib import Path
import sys
import unittest

import term_refutation as t

E = t.P / "evidence/term-refutation"
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / "execution"
sys.argv[1:] = []
ROWS = json.loads((E / "examples/summary.json").read_text())["rows"]
PACKETS = {row["id"]: t.k.load_packet(E / "examples" / (row["id"] + ".json")) for row in ROWS}


def reseal(packet):
    packet["identity"] = t.canonical_identity(packet)
    return packet


def leaf(op, value):
    return {"formal/term": 1, "op": op, "sort": [op], "data": value, "args": []}


class TermChecks(unittest.TestCase):
    def test_original_terms_of_real_bl_certificates_are_checked(self):
        records = []
        for name in PACKETS:
            with self.subTest(name=name):
                result = t.run(E / "examples" / (name + ".json"), OUTPUT / name)
                self.assertEqual(result["status"], "checked-term-entailment")
                self.assertEqual(result["normalization_connection"], "checked-countermodel-preservation-for-this-question")
                self.assertEqual(result["axioms"]["originalQuestionEntails"], ["propext", "Quot.sound"])
                self.assertFalse(result["compiler_proof_authority"])
                records.append({"id": name, **result})
        self.assertEqual(len(records), 17)
        (OUTPUT / "accepted.json").write_text(json.dumps(records, indent=2) + "\n")

    def test_valid_normalized_refutations_cannot_establish_false_original_claims(self):
        cases = {}
        packet = copy.deepcopy(PACKETS["weighted"])
        packet["claim"] = leaf("bool", False)
        cases["false-original-claim"] = packet
        packet = copy.deepcopy(PACKETS["weighted"])
        packet["assertions"] = []
        cases["dropped-original-assumptions"] = packet
        packet = copy.deepcopy(PACKETS["weighted"])
        division = {"formal/term": 1, "op": "div", "sort": ["int"], "data": None, "args": [leaf("int", 7), leaf("int", 0)]}
        packet["claim"] = {"formal/term": 1, "op": "eq", "sort": ["bool"], "data": None, "args": [division, leaf("int", 0)]}
        cases["undefined-original-claim"] = packet
        packet = copy.deepcopy(PACKETS["increment"])
        # The original x cancels out of the old normalized packet. A changed
        # right operand must still be checked against the full original trees.
        packet["claim"]["args"][1]["args"][1]["data"] = "different-input"
        cases["erased-variable-changed-before-normalization"] = packet
        packet = copy.deepcopy(PACKETS["boolean-choice"])
        packet["claim"]["args"][1]["args"][0]["args"][1] = copy.deepcopy(packet["claim"]["args"][1]["args"][0]["args"][0])
        cases["selected-branch-changed"] = packet
        records = []
        for name, packet in cases.items():
            with self.subTest(name=name):
                reseal(packet)
                t.validate(packet)
                target = OUTPUT / "rejected" / name
                target.mkdir(parents=True, exist_ok=True)
                path = target / "packet.json"; path.write_text(json.dumps(packet) + "\n")
                with self.assertRaisesRegex(ValueError, "Lean did not accept"):
                    t.run(path, target)
                self.assertTrue((target / "lean.txt").exists())
                self.assertFalse((target / "Check.olean").exists())
                records.append({"id": name, "status": "rejected-by-lean", "packet": packet["identity"],
                                "normalized_refutation": "unchanged-from-accepted-original"})
        (OUTPUT / "rejected.json").write_text(json.dumps(records, indent=2) + "\n")

    def test_original_source_and_variable_maps_are_independently_decoded(self):
        for packet in PACKETS.values():
            integers, booleans = t.validate(packet)
            source = t.source(packet, integers, booleans)
            t.verify_source(source, packet, integers, booleans)
            for name in integers + booleans:
                self.assertNotIn(name, source)
        packet = PACKETS["weighted"]
        integers, booleans = t.validate(packet)
        source = t.source(packet, integers, booleans)
        changes = [
            source.replace("Term.inputInt 0", "Term.inputInt 1", 1),
            source.replace("Term.le", "Term.lt", 1),
            source.replace("Term.and", "Term.or", 1),
            source.replace("Term.bool true", "Term.bool false", 1),
            source.replace("([0, 1] : List Nat)", "([1, 0] : List Nat)", 1),
            source.replace("by decide", "by native_decide"),
            source.replace("normalizationConnected packetAccepted", "(by sorry) packetAccepted"),
            source.replace("import Terms", "import Other"),
            source + "\naxiom forged : False\n",
        ]
        for index, changed in enumerate(changes):
            with self.subTest(index=index):
                self.assertNotEqual(changed, source)
                with self.assertRaises(ValueError):
                    t.verify_source(changed, packet, integers, booleans)

    def test_original_schema_rejects_type_confusion_and_missing_data(self):
        alterations = [lambda p: p.update(identity="0" * 64), lambda p: p.update(semantics="different"),
                      lambda p: p.update(extra=True), lambda p: p.update(claim=leaf("int", 0)),
                      lambda p: p.update(claim=leaf("bool", 1)), lambda p: p.update(claim=leaf("int", True)),
                      lambda p: p["claim"].update(sort=["real"]), lambda p: p["claim"].update(op="invoke"),
                      lambda p: p["claim"].update(data="opaque"), lambda p: p["claim"].update(args=[])]
        for index, change in enumerate(alterations):
            with self.subTest(index=index):
                packet = copy.deepcopy(PACKETS["weighted"]); change(packet)
                with self.assertRaises(ValueError):
                    t.validate(packet)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    unittest.main(verbosity=2)
