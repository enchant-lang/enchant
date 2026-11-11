"""Exercise real adapter packets and challenge the independent trace proof."""
import copy
import json
from pathlib import Path
import sys
import unittest

import core_observation_check as check

E = check.actor.P / 'evidence/core-observations'
EXAMPLES = E / 'examples'
SAFETY = E.parent / 'core-actors/examples'
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
CASES = {
    'bank': ('safe', None, None),
    'context-counter': ('safe', None, None),
    'overlapping-message-names': ('safe', None, None),
    'full-idle': ('safe', None, None),
    'initial-only': ('safe', None, None),
    'failure': ('unsafe', 2, None),
    'unsafe-return': ('unsafe', None, 1),
}


def load(name):
    return check.k.load_packet(EXAMPLES / f'{name}.json')


def reseal(packet, directory):
    directory.mkdir(parents=True, exist_ok=True)
    packet['identity'] = check.canonical_identity(packet)
    path = directory / 'packet.json'
    path.write_text(json.dumps(packet, indent=2) + '\n')
    return path


class CoreObservationChecks(unittest.TestCase):
    def test_recorded_prefixes_and_exact_safety_composition(self):
        rows = []
        for name, (safety, failure, violation) in CASES.items():
            with self.subTest(case=name):
                packet = load(name)
                result = check.run(EXAMPLES / f'{name}.json', OUT / name, 'choice-free')
                self.assertEqual(result['status'], 'checked-recorded-core-trace')
                self.assertEqual(result['packet'], packet['identity'])
                self.assertEqual(result['observation'], packet['observation'])
                self.assertEqual(result['checked_prefixes'], len(packet['frames']))
                self.assertEqual(result['recorded_safety'], safety)
                self.assertEqual(result['first_failure_at'], failure)
                self.assertEqual(result['first_invariant_violation_at'], violation)
                self.assertFalse(result['compiler_proof_authority'])
                self.assertEqual(result['execution_authenticity'], 'observer-trusted')
                self.assertIsNone(result['all_traces_safety_packet'])
                for index, frame in enumerate(packet['frames']):
                    self.assertIn(f'CoreObservedTrace.recordedPrefix{index}', result['axioms'])
                    if frame['kind'] in ('returned', 'raised'):
                        self.assertIn(f'CoreObservedTrace.recordedMessage{index}Read', result['axioms'])
                if safety == 'safe':
                    self.assertIn(f"CoreObservedTrace.recordedSafe{len(packet['frames']) - 1}", result['axioms'])
                else:
                    self.assertIn('CoreObservedTrace.recordedUnsafePrefix', result['axioms'])
                rows.append({'id': name, **result})
        self.assertEqual(len(rows), len(CASES))
        linked = check.run(EXAMPLES / 'bank.json', OUT / 'bank-linked', safety_path=SAFETY / 'bank.json')
        self.assertEqual(linked['all_traces_safety_packet'], check.k.load_packet(SAFETY / 'bank.json')['identity'])
        self.assertEqual(linked['packet'], load('bank')['identity'])
        for index in range(linked['checked_prefixes']):
            name = f'CoreObservedTrace.recordedSafe{index}'
            self.assertIn('Classical.choice', linked['axioms'][name])
            self.assertIn(f'originalHandlerTracesSafe recordedPrefix{index}', (OUT / 'bank-linked/CoreObservedTrace.lean').read_text())
        rows.append({'id': 'bank-linked', **linked})
        (OUT / 'accepted.json').write_text(json.dumps(rows, indent=2) + '\n')

    def test_resealed_false_steps_and_invariant_claims_are_rejected_by_lean(self):
        packets = []
        original = load('bank')
        wrong_initial = copy.deepcopy(original)
        wrong_initial['frames'][0]['state'][0][1] = 1
        packets.append(('wrong-initial', wrong_initial, 'recordedPrefix0'))
        wrong_return = copy.deepcopy(original)
        wrong_return['frames'][1]['state'][0][1] = 11
        wrong_return['frames'][1]['state'][1][1] = 11
        packets.append(('wrong-return', wrong_return, 'recordedStep1'))
        outside = copy.deepcopy(original)
        outside['frames'][1]['message'][0][1] = -1
        outside['frames'][1]['state'][0][1] = -1
        outside['frames'][1]['state'][1][1] = -1
        outside['frames'][1]['invariant'] = 'violated'
        packets.append(('outside-admission', outside, 'recordedStep1'))
        wrong_idle = load('failure')
        wrong_idle['frames'][3]['state'][0][1] = 88
        packets.append(('changed-state-during-idle', wrong_idle, 'recordedStep3'))
        changed_failure = load('failure')
        changed_failure['frames'][2]['state'][0][1] = 8
        packets.append(('commit-on-raise', changed_failure, 'recordedStep2'))
        resumed = load('failure')
        resumed['frames'][3] = {'kind': 'returned', 'handler': 'compute', 'message': [['divisor', 1]],
                                'state': [['n', -2]], 'invariant': 'holds'}
        packets.append(('resumed-after-raise', resumed, 'recordedStep3'))
        wrong_invariant = load('unsafe-return')
        wrong_invariant['frames'][1]['invariant'] = 'holds'
        packets.append(('wrong-invariant', wrong_invariant, 'recordedInvariant1'))
        rows = []
        for name, packet, theorem in packets:
            with self.subTest(case=name):
                directory = OUT / 'rejected' / name
                path = reseal(packet, directory)
                check.validate(packet)
                (directory / 'CoreObservedTrace.olean').write_bytes(b'stale object')
                (directory / 'result.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept the exact recorded Core trace'):
                    check.run(path, directory, 'choice-free')
                transcript = (directory / 'lean.txt').read_text()
                self.assertIn(theorem, transcript)
                self.assertFalse((directory / 'CoreObservedTrace.olean').exists())
                self.assertFalse((directory / 'result.json').exists())
                rows.append({'id': name, 'packet': packet['identity'], 'status': 'not-accepted-by-Lean'})
        self.assertEqual(len(rows), len(packets))
        (OUT / 'rejected.json').write_text(json.dumps(rows, indent=2) + '\n')

    def test_subject_projection_and_generated_data_checks(self):
        packet = load('overlapping-message-names')
        layouts = check.validate(packet)
        source = check.source(packet, layouts, False)
        check.verify_source(source, packet, layouts, False)
        with self.assertRaisesRegex(ValueError, 'generated actor state or proof slots differ'):
            check.verify_source(source.replace('(recordedInputs [(Int.ofNat 0)] [false, true])',
                                               '(recordedInputs [(Int.ofNat 0)] [false, false])', 1), packet, layouts, False)
        reversed_artifacts = load('bank')
        reversed_artifacts['observation']['artifacts'].reverse()
        reversed_artifacts['identity'] = check.canonical_identity(reversed_artifacts)
        with self.assertRaisesRegex(ValueError, 'exact observation artifact handler'):
            check.validate(reversed_artifacts)
        with self.assertRaisesRegex(ValueError, 'different exact actor model'):
            check.run(EXAMPLES / 'bank.json', OUT / 'wrong-safety', safety_path=SAFETY / 'context-counter.json')

    def test_receipt_identity_is_a_data_link_requiring_bl_reconstruction(self):
        packet = load('context-counter')
        packet['observation']['receipt'] = '0' * 64
        directory = OUT / 'changed-receipt-label'
        result = check.run(reseal(packet, directory), directory, 'choice-free')
        self.assertEqual(result['recorded_safety'], 'safe')
        self.assertEqual(result['receipt_connection'], 'requires-fresh-BL-reconstruction')
        self.assertEqual(result['execution_authenticity'], 'observer-trusted')


if __name__ == '__main__':
    unittest.main()
