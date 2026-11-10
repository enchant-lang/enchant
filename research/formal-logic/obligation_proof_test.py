"""Check real common manifests and the boundaries of their declared coverage."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import obligation_proof as o

E = o.P / "evidence/obligations"
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / "execution"
sys.argv[1:] = []
EXAMPLES = E / "examples"
ROWS = json.loads((EXAMPLES / "summary.json").read_text())["rows"]
MANIFESTS = {row["id"]: o.terms.k.load_packet(EXAMPLES / row["manifest-file"]) for row in ROWS}


def reseal(manifest):
    manifest["identity"] = o.canonical_identity(manifest)
    return manifest


class ObligationChecks(unittest.TestCase):
    def test_every_subject_manifest_has_checked_or_explicitly_pending_coverage(self):
        results = []
        for row in ROWS:
            with self.subTest(subject=row["id"]):
                result = o.run(EXAMPLES / row["manifest-file"], OUTPUT / row["id"])
                expected = "checked-required-term-evidence" if row["expected"] == "ready" else "incomplete-obligation-evidence"
                self.assertEqual(result["status"], expected)
                for key in ["required", "ready", "complete", "unreachable"]:
                    self.assertEqual(result["coverage"][key], row["coverage"][key])
                self.assertEqual(result["positive_feasibility"], "not-established")
                self.assertEqual(result["model_theorem"], "not-established-by-this-runner")
                self.assertFalse(result["compiler_proof_authority"])
                if row["id"] == "vacuous":
                    self.assertEqual(result["initial_assumption_consistency"], "inconsistent-in-contained-typed-term-model")
                else:
                    self.assertEqual(result["initial_assumption_consistency"], "not-established")
                results.append({"id": row["id"], **result})
        self.assertEqual(len(results), 13)
        self.assertEqual(sum(r["coverage"]["ready"] for r in results), 22)
        self.assertEqual(sum(len(r["checked"]) for r in results), 23)
        self.assertEqual(sum(r["coverage"]["unreachable"] for r in results), 1)
        (OUTPUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")

    def test_false_goal_cannot_be_replaced_by_an_unrelated_true_theorem(self):
        ordinary = next(row["packet"] for row in MANIFESTS["query"]["rows"] if row["status"] == "ready")
        for name, role in [("vacuous", "inconsistency"), ("unreachable", "unreachable")]:
            with self.subTest(name=name):
                manifest = copy.deepcopy(MANIFESTS[name])
                row = next(row for row in manifest["rows"] if (row["role"] == role if role == "inconsistency" else row["via"] == role))
                row["packet"] = copy.deepcopy(ordinary)
                row["unreachable" if role == "unreachable" else "question"] = ordinary["normalized"]["question"]
                reseal(manifest)
                with self.assertRaisesRegex(ValueError, "explicit false goal"):
                    o.validate(manifest)

    def test_manifest_schema_preserves_obligation_witness_and_authority_distinctions(self):
        edits = [lambda m: m.update(identity="0" * 64), lambda m: m.update(**{"compiler-proof-authority": True}),
                 lambda m: m.update(feasibility="proved-sat"), lambda m: m.update(composition="proved"),
                 lambda m: m.update(rows=[]), lambda m: m["rows"][2].update(required=1),
                 lambda m: m["rows"][2].update(required=False), lambda m: m["rows"][2].update(via="witness"),
                 lambda m: m["rows"][2].update(question="0" * 64), lambda m: m["rows"][0].update(packet=m["rows"][2]["packet"]),
                 lambda m: m["rows"].append(copy.deepcopy(m["rows"][2]))]
        for index, edit in enumerate(edits):
            with self.subTest(index=index):
                manifest = copy.deepcopy(MANIFESTS["contract"]); edit(manifest)
                with self.assertRaises(ValueError):
                    o.validate(manifest)
        manifest = copy.deepcopy(MANIFESTS["sat"])
        manifest["rows"][0].update(status="ready", packet=MANIFESTS["query"]["rows"][2]["packet"])
        reseal(manifest)
        with self.assertRaisesRegex(ValueError, "SAT witness"):
            o.validate(manifest)

    def test_a_declared_subset_is_not_a_proof_of_full_model_coverage(self):
        # A manifest-only tool cannot reconstruct an arbitrary original model.
        # The BL checker separately rejects this omission against its full plan.
        manifest = copy.deepcopy(MANIFESTS["loop"])
        manifest["rows"] = [next(row for row in manifest["rows"] if row["required"])]
        reseal(manifest); o.validate(manifest)
        target = OUTPUT / "declared-subset"; target.mkdir(parents=True, exist_ok=True)
        path = target / "manifest.json"; path.write_text(json.dumps(manifest) + "\n")
        result = o.run(path, target)
        self.assertEqual(result["coverage"]["required"], 1)
        self.assertEqual(result["model_connection"], "requires-fresh-BL-subject-plan-reconstruction")
        self.assertEqual(result["model_theorem"], "not-established-by-this-runner")
        self.assertFalse(result["compiler_proof_authority"])

    def test_missing_sat_witness_has_a_distinct_unsuccessful_cli_exit(self):
        completed = subprocess.run([sys.executable, str(o.P / "obligation_proof.py"), str(EXAMPLES / "manifests/sat.json"),
                                    "--output", str(OUTPUT / "sat-cli")], capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "incomplete-obligation-evidence")
        self.assertFalse((OUTPUT / "sat-cli/rows").exists())


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    unittest.main(verbosity=2)
