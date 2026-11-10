"""Check the actual BL-exported outcomes and reject semantic substitutions."""
import copy
import json
from pathlib import Path
import sys
import unittest

import core_term_check as bridge

E = bridge.P / 'evidence/core-terms'
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
ROWS = json.loads((E / 'examples/summary.json').read_text())['rows']
PACKETS = {row['id']: bridge.k.load_packet(E / 'examples' / f"{row['id']}.json") for row in ROWS}


def literal(sort, value):
    return {'formal/term': 1, 'op': sort, 'sort': [sort], 'data': value, 'args': []}


def reseal(packet):
    packet['identity'] = bridge.canonical_identity(packet)
    return packet


class CoreTermChecks(unittest.TestCase):
    def test_all_exported_trees_agree_with_their_actual_symbolic_outcomes(self):
        results = []
        for row in ROWS:
            name = row['id']
            with self.subTest(case=name):
                checked = bridge.run(E / 'examples' / f'{name}.json', OUTPUT / name)
                self.assertEqual(checked['status'], 'checked-core-term-correspondence')
                self.assertEqual(checked['packet'], row['packet'])
                self.assertEqual(checked['subject'], row['subject'])
                self.assertFalse(checked['compiler_proof_authority'])
                self.assertEqual(set(checked['axioms']), {'coreTermCorrespondence', 'errorCatalogueRoundTrip'})
                results.append({'id': name, **checked})
        self.assertEqual(len(results), 34)
        (OUTPUT / 'accepted.json').write_text(json.dumps(results, indent=2) + '\n')

    def test_well_formed_resealed_changes_fail_the_universal_proof(self):
        wrong = {}
        packet = copy.deepcopy(PACKETS['arithmetic']); packet['outcome']['value'] = literal('int', 0)
        wrong['changed-arithmetic-value'] = packet
        packet = copy.deepcopy(PACKETS['eager-default']); packet['outcome']['ok'] = literal('bool', True)
        wrong['eager-default-changed-to-success'] = packet
        packet = copy.deepcopy(PACKETS['named-first-error']); packet['outcome']['error'] = literal('int', dict(packet['errors'])['phase/right'])
        wrong['second-error-replaces-first'] = packet
        packet = copy.deepcopy(PACKETS['record-order']); packet['body']['data'].reverse(); packet['body']['args'].reverse()
        wrong['record-evaluation-order-reversed'] = packet
        packet = copy.deepcopy(PACKETS['quotient'])
        packet['outcome']['value'] = {'formal/term': 1, 'op': 'div', 'sort': ['int'], 'data': None,
                                     'args': [row[2] for row in packet['inputs']]}
        wrong['euclidean-division-replaces-quotient'] = packet
        packet = copy.deepcopy(PACKETS['record-construction']); packet['outcome']['value'][1][1] = literal('int', 0)
        wrong['returned-record-field-replaced'] = packet
        rejected = []
        for name, packet in wrong.items():
            with self.subTest(case=name):
                bridge.validate(reseal(packet))
                target = OUTPUT / 'rejected' / name
                target.mkdir(parents=True, exist_ok=True)
                path = target / 'packet.json'; path.write_text(json.dumps(packet) + '\n')
                (target / 'Check.olean').write_bytes(b'stale object')
                (target / 'result.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept'):
                    bridge.run(path, target)
                self.assertFalse((target / 'Check.olean').exists())
                self.assertFalse((target / 'result.json').exists())
                self.assertTrue((target / 'lean.txt').exists())
                rejected.append({'id': name, 'packet': packet['identity'], 'status': 'not-accepted-by-Lean'})
        (OUTPUT / 'rejected.json').write_text(json.dumps(rejected, indent=2) + '\n')

    def test_failure_payload_is_outside_the_outcome_relation(self):
        packet = copy.deepcopy(PACKETS['named-first-error'])
        packet['outcome']['value'] = literal('int', 999)
        target = OUTPUT / 'ignored-failure-payload'
        target.mkdir(parents=True, exist_ok=True)
        path = target / 'packet.json'; path.write_text(json.dumps(reseal(packet)) + '\n')
        self.assertEqual(bridge.run(path, target)['status'], 'checked-core-term-correspondence')

    def test_decoder_checks_lexical_slots_shaped_inputs_and_term_sources(self):
        for packet in PACKETS.values():
            ints, bools = bridge.validate(packet)
            bridge.verify_source(bridge.source(packet, ints, bools), packet, ints, bools)
        packet = PACKETS['named-paths']
        ints, bools = bridge.validate(packet)
        source = bridge.source(packet, ints, bools)
        self.assertNotIn('λ', source)
        self.assertNotIn('\0', source)
        for changed in [source.replace('Var.zero', '(Var.succ Var.zero)', 1),
                        source.replace('(i 0)', '(i 1)', 1),
                        source.replace('by decide', 'by sorry')]:
            with self.assertRaises(ValueError):
                bridge.verify_source(changed, packet, ints, bools)
        bad = copy.deepcopy(PACKETS['record-construction'])
        bad['outcome']['value'].reverse()
        with self.assertRaisesRegex(ValueError, 'canonical named payload field'):
            bridge.validate(reseal(bad))

    def test_arithmetic_dependency_obeys_the_selected_axiom_policy(self):
        target = OUTPUT / 'choice-free-quotient'
        with self.assertRaisesRegex(ValueError, 'Core term axioms exceed policy'):
            bridge.run(E / 'examples/quotient.json', target, 'choice-free')
        self.assertFalse((target / 'Check.olean').exists())
        self.assertIn('Classical.choice', (target / 'lean.txt').read_text())


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    unittest.main(verbosity=2)
