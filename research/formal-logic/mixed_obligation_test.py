"""Check mixed obligation bundles, exact context links and applied claims."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import obligation_proof as proof
import obligation_instance as instance
import witness_kernel as witnesses

E = proof.P / 'evidence/mixed-obligations'
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
EXAMPLES = E / 'examples'
ROWS = json.loads((EXAMPLES / 'summary.json').read_text())['rows']
MANIFESTS = {row['id']: proof.terms.k.load_packet(EXAMPLES / row['manifest-file']) for row in ROWS}


def reseal(manifest):
    manifest['identity'] = proof.canonical_identity(manifest)
    return manifest


class MixedObligationChecks(unittest.TestCase):
    def test_all_subjects_check_leaves_and_apply_matching_entailments(self):
        results = []
        for row in ROWS:
            name = row['id']
            with self.subTest(subject=name):
                result = proof.run(EXAMPLES / row['manifest-file'], OUTPUT / name)
                self.assertEqual(result['coverage'], {k: v for k, v in row['coverage'].items() if k != 'pending'})
                self.assertEqual(result['entailments_with_witnessed_context'], row['entailments-with-witnessed-context'])
                self.assertEqual(result['positive_feasibility'], 'satisfiable-in-contained-typed-term-model'
                                 if row['initial-evidence'] == 'witness-ready' else 'not-established')
                self.assertEqual(result['model_theorem'], 'not-established-by-this-runner')
                self.assertFalse(result['compiler_proof_authority'])
                for checked in result['checked_instances']:
                    root = OUTPUT / name / 'instances' / f"{checked['index']:04d}"
                    self.assertEqual(checked['status'], 'checked-original-question-satisfying-claim')
                    self.assertEqual(proof.terms.k.sha(root / 'Instance.olean'), checked['olean_sha256'])
                    self.assertEqual(set(checked['axioms']), {'chosenWitnessAccepted', 'chosenClaim', 'originalQuestionHasSatisfyingClaim'})
                results.append({'id': name, **result})
        self.assertEqual(len(results), 17)
        self.assertEqual(sum(len(row['checked']) for row in results), 39)
        self.assertEqual(sum(len(row['checked_instances']) for row in results), 11)
        self.assertEqual(sum(row['coverage']['witnesses'] for row in results), 3)
        layout = next(row for row in results if row['id'] == 'named-layout')['checked_instances'][0]
        text = (OUTPUT / 'named-layout' / 'instances' / f"{layout['index']:04d}" / 'Instance.lean').read_text()
        self.assertEqual(witnesses.decode_witness(text[len(instance.HEADER):-len(instance.TAIL)]), ([0, 7], []))
        (OUTPUT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')

    def test_context_identity_compares_original_assertions_without_tautology_padding(self):
        manifest = MANIFESTS['named-layout']
        leaves = [row for row in manifest['rows'] if row['status'] == 'ready']
        self.assertEqual(len(leaves), 2)
        self.assertEqual(leaves[0]['context'], leaves[1]['context'])
        assertions = leaves[0]['packet']['assertions']
        self.assertEqual(proof.context_identity(assertions), proof.context_identity([proof.TRUE_TERM, *reversed(assertions), *assertions]))
        self.assertNotEqual(proof.context_identity(assertions), proof.context_identity([]))
        for field in ['question', 'context']:
            changed = copy.deepcopy(manifest)
            changed['rows'][1][field] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'witness packet belongs|witness assertion context'):
                proof.validate(reseal(changed))

    def test_inconsistent_context_and_ready_witness_cannot_be_assembled(self):
        changed = copy.deepcopy(MANIFESTS['contract'])
        false = copy.deepcopy(MANIFESTS['vacuous']['rows'][0])
        initial = changed['rows'][1]
        false['packet']['assertions'] = initial['packet']['assertions']
        false['packet']['identity'] = proof.terms.canonical_identity(false['packet'])
        false['context'] = initial['context']
        changed['rows'][0] = false
        with self.assertRaisesRegex(ValueError, 'witness and false-goal evidence conflict'):
            proof.validate(reseal(changed))
        changed = copy.deepcopy(MANIFESTS['contract'])
        changed['rows'][0]['context'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'must share an assertion context'):
            proof.validate(reseal(changed))

    def test_resealed_false_witness_fails_lean_and_removes_old_success(self):
        output = OUTPUT / 'rejected-witness'
        proof.run(EXAMPLES / 'manifests/sat.json', output)
        self.assertTrue((output / 'result.json').is_file())
        changed = copy.deepcopy(MANIFESTS['sat'])
        packet = changed['rows'][0]['packet']
        packet['bindings'][0][2] = -1
        packet['identity'] = witnesses.canonical_identity(packet)
        path = output / 'changed.json'
        path.write_text(json.dumps(reseal(changed)) + '\n')
        proof.validate(changed)
        with self.assertRaisesRegex(ValueError, 'Lean did not accept typed-term witness'):
            proof.run(path, output)
        self.assertFalse((output / 'result.json').exists())
        self.assertFalse((output / 'rows/0000/Check.olean').exists())
        self.assertTrue((output / 'rows/0000/lean.txt').exists())

    def test_required_witness_cli_coverage_in_both_directions(self):
        for name, expected in [('sat', 0), ('sat-no-witness', 2)]:
            result = subprocess.run([sys.executable, str(proof.P / 'obligation_proof.py'), str(EXAMPLES / f'manifests/{name}.json'),
                                     '--output', str(OUTPUT / f'cli-{name}')], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['coverage']['witnesses'], int(expected == 0))


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    unittest.main(verbosity=2)
