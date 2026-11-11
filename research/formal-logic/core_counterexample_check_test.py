"""Check native discoveries and refuse individually valid but mismatched evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest

import core_counterexample_check as check

E = check.terms.P / 'evidence/core-counterexamples'
EXAMPLES = E / 'examples'
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []


def load(name):
    return check.k.load_packet(EXAMPLES / (name + '.json'))


def reseal(packet, output):
    output.mkdir(parents=True, exist_ok=True)
    packet['identity'] = check.canonical_identity(packet)
    path = output / 'packet.json'
    path.write_text(json.dumps(packet, indent=2) + '\n')
    return path


class CoreCounterexampleChecks(unittest.TestCase):
    def test_original_queries_match_both_engines_and_exact_recorded_runs(self):
        index = json.loads((EXAMPLES / 'summary.json').read_text())
        rows = []
        for row in index['rows']:
            name = row['id']
            with self.subTest(case=name):
                result = check.run(EXAMPLES / (name + '.json'), OUT / name)
                self.assertEqual(result['status'], 'checked-original-query-and-unsafe-core-run')
                self.assertEqual(result['packet'], row['packet'])
                self.assertEqual(result['subject']['identity'], row['subject'])
                self.assertEqual(result['subject']['query'], row['query'])
                self.assertEqual(result['receipt'], row['receipt'])
                self.assertEqual(result['discovery']['engine'], row['engine'])
                self.assertEqual(result['checked_prefixes'], row['events'] + 1)
                self.assertIn('CoreCounterexampleCheck.originalCounterexampleRuns', result['axioms'])
                self.assertTrue(all('Classical.choice' not in deps for deps in result['axioms'].values()))
                self.assertFalse(result['compiler_proof_authority'])
                self.assertEqual(result['general_unrolling_correspondence'], 'not-established')
                self.assertEqual(result['execution_authenticity'], 'observer-trusted')
                rows.append({'id': name, **result})
        self.assertEqual(len(rows), 12)
        self.assertEqual(sum(row['checked_prefixes'] for row in rows), 26)
        for case in {row['case'] for row in index['rows']}:
            pair = [row for row in rows if row['id'].startswith(case + '-')]
            self.assertEqual(len(pair), 2)
            self.assertEqual(pair[0]['subject'], pair[1]['subject'])
        for engine in ('z3', 'oxiz'):
            overdraft = next(row for row in rows if row['id'] == 'overdraft-' + engine)
            self.assertGreater(overdraft['extra_observation_bindings'], 0)
        oxiz = next(row for row in rows if row['id'] == 'overdraft-oxiz')
        self.assertGreater(oxiz['completion_origins']['explicit-replay-completion'], 0)
        (OUT / 'accepted.json').write_text(json.dumps(rows, indent=2) + '\n')

    def test_individually_valid_trace_and_query_must_have_the_same_projection(self):
        original = load('overdraft-z3')
        wrong_run = copy.deepcopy(original)
        frames = wrong_run['execution']['frames']
        amount = frames[1]['message'][0][1]
        frames[1]['message'][0][1] = amount + 1
        frames[1]['state'][0][1] = -(amount + 1)
        wrong_run['execution']['identity'] = check.observed.canonical_identity(wrong_run['execution'])
        swapped_states = copy.deepcopy(original)
        swapped_states['layout']['states'].reverse()
        swapped_messages = copy.deepcopy(original)
        # Swapping two distinct Boolean slots preserves both original leaf proofs.
        state_flag = swapped_messages['layout']['states'][0][1]
        ignored = swapped_messages['layout']['inputs'][0][0][1][1]
        state_flag[1], ignored[1] = ignored[1], state_flag[1]
        rows = []
        for name, packet, theorem in [('different-valid-unsafe-run', wrong_run, 'projectedState1Matches'),
                                      ('reversed-state-layout', swapped_states, 'projectedState0Matches'),
                                      ('wrong-Boolean-field', swapped_messages, 'projectedState0Matches')]:
            with self.subTest(case=name):
                output = OUT / 'rejected' / name
                path = reseal(packet, output)
                check.validate(packet)
                (output / 'CoreCounterexampleCheck.olean').write_bytes(b'stale success')
                (output / 'result.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept the original counterexample and recorded projection'):
                    check.run(path, output)
                self.assertTrue((output / 'trace/CoreObservedTrace.olean').exists())
                self.assertTrue((output / 'witness/Check.olean').exists())
                self.assertEqual(json.loads((output / 'trace/result.json').read_text())['recorded_safety'], 'unsafe')
                self.assertIn(theorem, (output / 'lean.txt').read_text())
                self.assertFalse((output / 'CoreCounterexampleCheck.olean').exists())
                self.assertFalse((output / 'result.json').exists())
                rows.append({'id': name, 'packet': packet['identity'], 'status': 'not-accepted-by-Lean',
                             'query_witness': 'checked', 'unsafe_trace': 'checked'})
        (OUT / 'rejected.json').write_text(json.dumps(rows, indent=2) + '\n')

    def test_query_identity_and_completed_bindings_keep_their_roles(self):
        packet = load('overdraft-oxiz')
        layout = check.validate(packet)
        source = check.source(packet, layout)
        check.verify_source(source, packet, layout)
        with self.assertRaisesRegex(ValueError, 'generated actor state or proof slots differ'):
            check.verify_source(source.replace('(suppliedWitness.integerEnv 0)', '(suppliedWitness.integerEnv 999)', 1),
                                packet, layout)
        different_goal = copy.deepcopy(packet)
        different_goal['claim'] = {'formal/term': 1, 'sort': ['bool'], 'op': 'bool', 'data': True, 'args': []}
        different_goal['identity'] = check.canonical_identity(different_goal)
        with self.assertRaisesRegex(ValueError, 'exact negated witness goal'):
            check.validate(different_goal)
        changed = copy.deepcopy(packet)
        name, sort, _ = changed['witness']['bindings'][0]
        binding = next(row for row in changed['bindings'] if row[0] == name)
        binding[2] = binding[2] + 1 if sort == ['int'] else not binding[2]
        changed['identity'] = check.canonical_identity(changed)
        with self.assertRaisesRegex(ValueError, 'SAT witness and trace binding values must agree'):
            check.validate(changed)
        context = load('context-overdraft-z3')
        context['subject']['profile'] = 'bl/source-record-trace-v1'
        context['identity'] = check.canonical_identity(context)
        with self.assertRaisesRegex(ValueError, 'recorded source, profile and depth'):
            check.validate(context)


if __name__ == '__main__':
    unittest.main()
