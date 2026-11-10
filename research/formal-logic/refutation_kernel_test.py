"""Sequential integration/adversarial checks for the real normalized bridge.

Run under one resource-capped systemd unit. Every successful proof is checked by
the pinned Lean kernel; negative proof cases must fail in Lean, not just schema.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import refutation_kernel as k

ROOT = k.PROJECT / "evidence/refutation-kernel"
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "execution"
sys.argv[1:] = []
ROWS = json.loads((ROOT / "examples/summary.json").read_text())["rows"]
PACKETS = {row["id"]: k.load_packet(ROOT / "examples" / (row["id"] + ".json")) for row in ROWS}


def reseal(packet):
    packet["identity"] = k.canonical_identity(packet)
    return packet


class BridgeChecks(unittest.TestCase):
    def test_real_bl_packets_apply_the_soundness_theorem(self):
        results = []
        for name in PACKETS:
            with self.subTest(name=name):
                result = k.run(ROOT / "examples" / (name + ".json"), OUTPUT / name)
                self.assertEqual(result["status"], "checked-normalized-refutation")
                self.assertEqual(result["axioms"]["packetAccepted"], ["propext"])
                self.assertEqual(result["axioms"]["packetUnsatisfiable"], ["propext", "Quot.sound"])
                self.assertFalse(result["compiler_proof_authority"])
                results.append({"id": name, **result})
        self.assertEqual(len(results), 11)
        (OUTPUT / "accepted.json").write_text(json.dumps(results, indent=2) + "\n")

    def test_validly_rehashed_false_refutations_are_rejected_by_lean(self):
        weighted = PACKETS["weighted"]
        cases = {}
        packet = copy.deepcopy(weighted)
        packet["kernel"]["proof"] = ["boolean"]
        cases["false-boolean-leaf"] = packet
        packet = copy.deepcopy(weighted)
        packet["kernel"]["proof"] = ["linear", [[0, 2], [1, 1], [2, 1]]]
        cases["unassigned-linear-premises"] = packet
        packet = copy.deepcopy(weighted)
        packet["kernel"]["proof"][2][2][3][1][0][1] = 1
        cases["altered-weight"] = packet
        packet = copy.deepcopy(weighted)
        packet["kernel"]["formulas"] = [["constant", True]]
        cases["satisfiable-normalized-problem"] = packet
        packet = copy.deepcopy(weighted)
        # The yes branch retains its accepted proof. The no branch must also
        # check, and cannot borrow the other branch's assignment or weights.
        packet["kernel"]["proof"][3] = ["linear", [[0, 1]]]
        cases["one-invalid-split-branch"] = packet
        records = []
        for name, packet in cases.items():
            with self.subTest(name=name):
                reseal(packet)
                k.validate(packet)
                target = OUTPUT / "rejected" / name
                target.mkdir(parents=True, exist_ok=True)
                path = target / "packet.json"
                path.write_text(json.dumps(packet) + "\n")
                with self.assertRaisesRegex(ValueError, "Lean did not accept"):
                    k.run(path, target)
                self.assertTrue((target / "lean.txt").is_file())
                self.assertFalse((target / "Check.olean").exists())
                records.append({"id": name, "status": "rejected-by-lean", "packet": packet["identity"]})
        (OUTPUT / "rejected.json").write_text(json.dumps(records, indent=2) + "\n")

    def test_schema_and_identity_fail_closed(self):
        alterations = [
            lambda p: p.update(identity="0" * 64),
            lambda p: p.update(rules=[]),
            lambda p: p.update(extra=True),
            lambda p: p.update(variables=["same", "same"]),
            lambda p: p["kernel"].update(proof=["split", True, ["boolean"], ["boolean"]]),
            lambda p: p["kernel"].update(proof=[["boolean"]]),
            lambda p: p["kernel"].update(proof=["linear", [[0, 0]]]),
            lambda p: p["kernel"].update(proof=["linear", [[0, -1]]]),
            lambda p: p["kernel"].update(proof=["linear", [[0, 2**4096]]]),
            lambda p: p["kernel"].update(formulas=[["atom", 32]]),
            lambda p: p["kernel"].update(formulas=[["constant", 1]]),
            lambda p: p["kernel"].update(formulas=[["both", ["constant", True]]]),
            lambda p: p["kernel"]["atoms"][0].__setitem__(1, [-2, 0]),
            lambda p: p["kernel"]["atoms"][0].__setitem__(1, [True, 0]),
        ]
        for index, change in enumerate(alterations):
            with self.subTest(index=index):
                packet = copy.deepcopy(PACKETS["weighted"])
                change(packet)
                with self.assertRaises(ValueError):
                    k.validate(packet)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for text in ['{"same":1,"same":2}', '{"value":NaN}', '{"value":Infinity}']:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    k.load_packet(path)

    def test_generated_source_is_independently_recovered(self):
        for packet in PACKETS.values():
            k.validate(packet)
            kernel = packet["kernel"]
            text = k.source(kernel)
            k.verify_source(text, kernel)
            for name in packet["variables"]:
                self.assertNotIn(name, text)
        kernel = PACKETS["weighted"]["kernel"]
        text = k.source(kernel)
        alterations = [
            text.replace("by decide", "by native_decide"),
            text.replace("by decide", "by sorry"),
            text.replace("import Refutation", "import Untrusted"),
            text.replace("Int.negSucc 1", "Int.negSucc 0", 1),
            text.replace("Formula.atom 0", "Formula.atom 1", 1),
            text.replace("Proof.split 0", "Proof.split 1", 1),
            text.replace("Problem.mk", "Problem.mk -- injected", 1),
            text + "\naxiom forged : False\n",
            text.replace(k.BETWEEN, "\naxiom forged : False\n" + k.BETWEEN),
            text.replace("Proof.boolean", "Proof.boolean Proof.boolean", 1),
        ]
        for index, changed in enumerate(alterations):
            with self.subTest(index=index):
                self.assertNotEqual(changed, text)
                with self.assertRaises((ValueError, IndexError)):
                    k.verify_source(changed, kernel)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    unittest.main(verbosity=2)
