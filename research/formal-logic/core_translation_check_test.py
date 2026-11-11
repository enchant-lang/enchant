"""Exercise both exact Core premises and changes to a translation question."""
import copy
import json
from pathlib import Path
import sys
import unittest

import core_translation_check as bridge

E = bridge.P / 'evidence/core-translations'
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
ROWS = json.loads((E / 'examples/summary.json').read_text())['rows']
PACKETS = {row['id']: bridge.k.load_packet(E / 'examples' / f"{row['id']}.json") for row in ROWS}


def bool_term(value):
    return {'formal/term': 1, 'op': 'bool', 'sort': ['bool'], 'data': value, 'args': []}


class CoreTranslationChecks(unittest.TestCase):
    def test_all_original_translations(self):
        results = []
        for row in ROWS:
            name = row['id']
            with self.subTest(case=name):
                policy = 'lean-standard' if name == 'signed-quotient' else 'choice-free'
                result = bridge.run(E / 'examples' / f'{name}.json', OUTPUT / name, policy)
                self.assertEqual(result['status'], 'checked-core-translation')
                self.assertEqual(result['packet'], row['packet'])
                self.assertEqual(result['subject'], row['subject'])
                self.assertFalse(result['compiler_proof_authority'])
                self.assertEqual(set(result['axioms']), bridge.AUDITS)
                self.assertEqual(set(result['imported_olean_sha256']), {'before', 'after', 'entailment'})
                results.append({'id': name, **result})
        self.assertEqual(len(results), 9)
        (OUTPUT / 'accepted.json').write_text(json.dumps(results, indent=2) + '\n')

    def test_valid_premises_cannot_prove_a_changed_comparison(self):
        changed_pre = copy.deepcopy(PACKETS['guarded-slots'])
        changed_pre['pre'] = bool_term(True)
        changed_after = copy.deepcopy(PACKETS['optimizer-preserves-failure'])
        changed_after['after'] = changed_after['before']
        changed_after['subject']['after'] = changed_after['subject']['before']
        rejected = []
        for name, packet in [('changed-precondition', changed_pre), ('different-checked-after', changed_after)]:
            with self.subTest(case=name):
                packet['identity'] = bridge.canonical_identity(packet)
                bridge.validate(packet)
                output = OUTPUT / 'rejected' / name
                output.mkdir(parents=True, exist_ok=True)
                path = output / 'packet.json'
                path.write_text(json.dumps(packet) + '\n')
                (output / 'CoreTranslationCheck.olean').write_bytes(b'stale object')
                (output / 'result.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept the exact Core translation composition'):
                    bridge.run(path, output, 'choice-free')
                self.assertFalse((output / 'CoreTranslationCheck.olean').exists())
                self.assertFalse((output / 'result.json').exists())
                self.assertIn('exactTranslationQuestion', (output / 'lean.txt').read_text())
                for side in ('before', 'after', 'entailment'):
                    self.assertTrue((output / side / 'Check.olean').exists())
                rejected.append({'id': name, 'packet': packet['identity'], 'status': 'not-accepted-by-Lean'})
        (OUTPUT / 'rejected.json').write_text(json.dumps(rejected, indent=2) + '\n')

    def test_shared_error_catalogue_and_exact_slot_decoder(self):
        bad = copy.deepcopy(PACKETS['both-named-errors'])
        errors = bad['after']['errors']
        errors[0][1], errors[1][1] = errors[1][1], errors[0][1]
        bad['after']['identity'] = bridge.core.canonical_identity(bad['after'])
        bad['identity'] = bridge.canonical_identity(bad)
        with self.assertRaisesRegex(ValueError, 'same named error catalogue'):
            bridge.validate(bad)
        packet = PACKETS['guarded-slots']
        layouts = bridge.validate(packet)
        source = bridge.source(packet, *layouts)
        bridge.verify_source(source, packet, *layouts)
        for slots in ('integerSlots', 'booleanSlots'):
            self.assertIn(f'{slots} : List Nat :=\n[1]', source)
            changed = source.replace(f'{slots} : List Nat :=\n[1]', f'{slots} : List Nat :=\n[0]')
            with self.assertRaisesRegex(ValueError, 'input slots differ'):
                bridge.verify_source(changed, packet, *layouts)


if __name__ == '__main__':
    unittest.main()
