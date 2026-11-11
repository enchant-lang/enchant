"""Check applied source handler trace proofs and challenge the exact assumptions."""
import copy
import json
from pathlib import Path
import sys
import unittest

import core_actor_check as bridge

E = bridge.P / 'evidence/core-actors'
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
ROWS = json.loads((E / 'examples/summary.json').read_text())['rows']
PACKETS = {row['id']: bridge.k.load_packet(E / 'examples' / f"{row['id']}.json") for row in ROWS}


def boolean(value):
    return {'formal/term': 1, 'op': 'bool', 'sort': ['bool'], 'args': [], 'data': value}


class CoreActorChecks(unittest.TestCase):
    def test_applied_trace_theorems(self):
        results = []
        for row in ROWS:
            name = row['id']
            with self.subTest(case=name):
                policy = 'lean-standard' if name == 'admission-protects-division' else 'choice-free'
                result = bridge.run(E / 'examples' / f'{name}.json', OUTPUT / name, policy)
                self.assertEqual(result['status'], 'checked-core-actor-trace-safety')
                self.assertEqual(result['packet'], row['packet'])
                self.assertEqual(result['subject'], row['subject'])
                self.assertIsNone(result['trace_bound'])
                self.assertFalse(result['compiler_proof_authority'])
                self.assertEqual(len(result['imported_olean_sha256']), 1 + 2 * result['handler_count'])
                self.assertIn('originalHandlerTracesSafe', result['axioms'])
                results.append({'id': name, **result})
        self.assertEqual(len(results), 6)
        self.assertEqual(sum(row['handler_count'] for row in results), 7)
        (OUTPUT / 'accepted.json').write_text(json.dumps(results, indent=2) + '\n')

    def test_valid_premises_cannot_prove_changed_admission_or_invariant(self):
        original = PACKETS['bank']
        widened = copy.deepcopy(original)
        widened['handlers'][0]['admission'] = boolean(True)
        changed_inv = copy.deepcopy(original)
        changed_inv['invariant'] = boolean(True)
        rejected = []
        for name, packet, theorem in [('widened-admission', widened, 'exactHandler0Question'),
                                      ('changed-invariant', changed_inv, 'exactInitialQuestion')]:
            with self.subTest(case=name):
                packet['identity'] = bridge.canonical_identity(packet)
                bridge.validate(packet)
                output = OUTPUT / 'rejected' / name
                output.mkdir(parents=True, exist_ok=True)
                path = output / 'packet.json'
                path.write_text(json.dumps(packet) + '\n')
                (output / 'CoreActorCheck.olean').write_bytes(b'stale object')
                (output / 'result.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept the exact Core actor trace composition'):
                    bridge.run(path, output)
                self.assertFalse((output / 'CoreActorCheck.olean').exists())
                self.assertFalse((output / 'result.json').exists())
                self.assertIn(theorem, (output / 'lean.txt').read_text())
                self.assertEqual(len(list(output.glob('*/Check.olean'))), 5)
                rejected.append({'id': name, 'packet': packet['identity'], 'status': 'not-accepted-by-Lean'})
        (OUTPUT / 'rejected.json').write_text(json.dumps(rejected, indent=2) + '\n')

    def test_manifest_and_state_slot_decoder(self):
        bad = copy.deepcopy(PACKETS['bank'])
        bad['handlers'].pop()
        bad['identity'] = bridge.canonical_identity(bad)
        with self.assertRaisesRegex(ValueError, 'complete ordered handler manifest'):
            bridge.validate(bad)
        packet = PACKETS['overlapping-message-names']
        layout = bridge.validate(packet)
        source = bridge.source(packet, layout)
        bridge.verify_source(source, packet, layout)
        self.assertIn('(Layout.bool 0)', source)
        with self.assertRaisesRegex(ValueError, 'state or proof slots differ'):
            bridge.verify_source(source.replace('(Layout.bool 0)', '(Layout.bool 1)', 1), packet, layout)


if __name__ == '__main__':
    unittest.main()
