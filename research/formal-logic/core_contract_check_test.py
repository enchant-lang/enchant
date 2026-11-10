"""Qualify exact contract composition and test changed premises."""
import copy
import json
from pathlib import Path
import sys
import unittest

import core_contract_check as bridge

E = bridge.P / 'evidence/core-contracts'
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
ROWS = json.loads((E / 'examples/summary.json').read_text())['rows']
PACKETS = {row['id']: bridge.k.load_packet(E / 'examples' / f"{row['id']}.json") for row in ROWS}


def boolean(value):
    return {'formal/term': 1, 'op': 'bool', 'sort': ['bool'], 'data': value, 'args': []}


class CoreContractChecks(unittest.TestCase):
    def test_all_original_contracts(self):
        results = []
        for row in ROWS:
            name = row['id']
            with self.subTest(case=name):
                result = bridge.run(E / 'examples' / f'{name}.json', OUTPUT / name, 'choice-free')
                self.assertEqual(result['status'], 'checked-core-contract')
                self.assertEqual(result['packet'], row['packet'])
                self.assertEqual(result['witness'], row['witness'])
                self.assertFalse(result['compiler_proof_authority'])
                self.assertIn('originalCoreSatisfiesContract', result['axioms'])
                self.assertEqual('originalCoreHasAdmittedOutcome' in result['axioms'], row['witness'] is not None)
                results.append({'id': name, **result})
        self.assertEqual(len(results), 8)
        self.assertEqual(sum(result['witness'] is not None for result in results), 6)
        (OUTPUT / 'accepted.json').write_text(json.dumps(results, indent=2) + '\n')

    def test_resealed_changes_fail_the_composed_proof(self):
        wrong = {}
        packet = copy.deepcopy(PACKETS['unused-slots'])
        packet['policy']['pre'] = boolean(True)
        wrong['changed-precondition'] = packet, 'exactContractQuestion'
        packet = copy.deepcopy(PACKETS['unused-slots'])
        packet['policy']['post'] = boolean(True)
        wrong['changed-postcondition'] = packet, 'exactContractQuestion'
        packet = copy.deepcopy(PACKETS['named-errors'])
        packet['policy']['must-return'] = True
        wrong['changed-return-policy'] = packet, 'exactContractQuestion'
        packet = copy.deepcopy(PACKETS['named-errors'])
        packet['policy']['allowed-codes'].pop()
        wrong['dropped-permitted-error'] = packet, 'exactContractQuestion'
        packet = copy.deepcopy(PACKETS['unused-slots'])
        witness = packet['witness']
        for binding in witness['bindings']:
            if binding[1] == ['int']:
                binding[2] = -1
        witness['identity'] = bridge.witnesses.canonical_identity(witness)
        wrong['precondition-false-in-witness'] = packet, 'chosenAdmitted'
        rejected = []
        for name, (packet, theorem) in wrong.items():
            with self.subTest(case=name):
                packet['identity'] = bridge.canonical_identity(packet)
                bridge.validate(packet)
                output = OUTPUT / 'rejected' / name
                output.mkdir(parents=True, exist_ok=True)
                path = output / 'packet.json'
                path.write_text(json.dumps(packet) + '\n')
                (output / 'CoreContractCheck.olean').write_bytes(b'stale object')
                (output / 'result.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept the exact Core contract composition'):
                    bridge.run(path, output, 'choice-free')
                self.assertFalse((output / 'CoreContractCheck.olean').exists())
                self.assertFalse((output / 'result.json').exists())
                self.assertIn(theorem, (output / 'lean.txt').read_text())
                self.assertEqual(json.loads((output / 'core/result.json').read_text())['status'], 'checked-core-term-correspondence')
                self.assertEqual(json.loads((output / 'entailment/result.json').read_text())['status'], 'checked-term-entailment')
                rejected.append({'id': name, 'packet': packet['identity'], 'status': 'not-accepted-by-Lean', 'theorem': theorem})
        (OUTPUT / 'rejected.json').write_text(json.dumps(rejected, indent=2) + '\n')

    def test_question_and_name_layout_connections(self):
        packet = copy.deepcopy(PACKETS['authored'])
        packet['entailment'] = PACKETS['source']['entailment']
        packet['identity'] = bridge.canonical_identity(packet)
        with self.assertRaisesRegex(ValueError, 'same contract question'):
            bridge.validate(packet)
        packet = PACKETS['unused-slots']
        layout = bridge.validate(packet)
        source = bridge.source(packet, *layout)
        self.assertIn('integerSlots : List Nat :=\n[1]', source)
        self.assertIn('booleanSlots : List Nat :=\n[1]', source)
        for slots in ('integerSlots', 'booleanSlots'):
            altered = source.replace(f'{slots} : List Nat :=\n[1]', f'{slots} : List Nat :=\n[0]')
            with self.assertRaisesRegex(ValueError, 'policy or input slots differ'):
                bridge.verify_source(altered, packet, *layout)
        self.assertNotIn('contract.core-contract-slots', source)


if __name__ == '__main__':
    unittest.main()
