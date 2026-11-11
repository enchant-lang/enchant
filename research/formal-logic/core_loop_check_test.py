"""Check applied ranked-loop proofs and independently challenge their connections."""
import copy
import json
from pathlib import Path
import sys
import unittest

import core_loop_check as bridge

E = bridge.P / 'evidence/core-loops'
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
ROWS = json.loads((E / 'examples/summary.json').read_text())['rows']
PACKETS = {row['id']: bridge.k.load_packet(E / 'examples' / f"{row['id']}.json") for row in ROWS}


def term_literal(sort, value):
    return {'formal/term': 1, 'op': sort, 'sort': [sort], 'args': [], 'data': value}


class CoreLoopChecks(unittest.TestCase):
    def test_checked_normal_return_of_the_original_loops(self):
        results = []
        for row in ROWS:
            name = row['id']
            with self.subTest(case=name):
                result = bridge.run(E / 'examples' / f'{name}.json', OUTPUT / name)
                self.assertEqual(result['status'], 'checked-core-loop-return')
                self.assertEqual(result['packet'], row['packet'])
                self.assertEqual(result['subject'], row['subject'])
                self.assertIsNone(result['iteration_bound'])
                self.assertFalse(result['compiler_proof_authority'])
                self.assertEqual(set(result['axioms']), bridge.AUDITS)
                self.assertIn('Classical.choice', result['axioms']['originalCoreLoopReturns'])
                results.append({'id': name, **result})
        self.assertEqual(len(results), 7)
        (OUTPUT / 'accepted.json').write_text(json.dumps(results, indent=2) + '\n')

    def test_valid_premises_cannot_prove_a_different_rank_or_postcondition(self):
        changed_rank = copy.deepcopy(PACKETS['countdown'])
        changed_rank['policy']['rank'] = [term_literal('int', 0)]
        changed_post = copy.deepcopy(PACKETS['boolean-state'])
        changed_post['policy']['ensures'] = term_literal('bool', True)
        rejected = []
        for name, packet in [('changed-rank', changed_rank), ('changed-postcondition', changed_post)]:
            with self.subTest(case=name):
                packet['identity'] = bridge.canonical_identity(packet)
                bridge.validate(packet)
                output = OUTPUT / 'rejected' / name
                output.mkdir(parents=True, exist_ok=True)
                path = output / 'packet.json'
                path.write_text(json.dumps(packet) + '\n')
                (output / 'CoreLoopCheck.olean').write_bytes(b'stale object')
                (output / 'result.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept the exact Core loop composition'):
                    bridge.run(path, output)
                self.assertFalse((output / 'CoreLoopCheck.olean').exists())
                self.assertFalse((output / 'result.json').exists())
                self.assertIn('exactLoopQuestion', (output / 'lean.txt').read_text())
                for side in ('initializer', 'controller', 'entailment'):
                    self.assertTrue((output / side / 'Check.olean').exists())
                rejected.append({'id': name, 'packet': packet['identity'], 'status': 'not-accepted-by-Lean'})
        (OUTPUT / 'rejected.json').write_text(json.dumps(rejected, indent=2) + '\n')

    def test_decoder_binds_original_control_order_and_state_slots(self):
        bad = copy.deepcopy(PACKETS['countdown'])
        bad['program']['state'].reverse()
        bad['program']['initial'].reverse()
        bad['identity'] = bridge.canonical_identity(bad)
        with self.assertRaisesRegex(ValueError, 'differ from the contained loop control'):
            bridge.validate(bad)
        packet = PACKETS['boolean-state']
        layouts = bridge.validate(packet)
        source = bridge.source(packet, layouts)
        self.assertIn('(Layout.bool 1)', source)
        changed = source.replace('(Layout.bool 1)', '(Layout.bool 0)', 1)
        with self.assertRaisesRegex(ValueError, 'state or proof slot layout differs'):
            bridge.verify_source(changed, packet, layouts)


if __name__ == '__main__':
    unittest.main()
