"""Real constructive witnesses, plus independently rehashed semantic attacks."""
import copy
import json
from pathlib import Path
import sys
import unittest

import witness_kernel as w

E = w.P / 'evidence/witnesses'
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else E / 'execution'
sys.argv[1:] = []
ROWS = json.loads((E / 'examples/summary.json').read_text())['rows']
PACKETS = {row['id']: w.k.load_packet(E / 'examples' / (row['id'] + '.json')) for row in ROWS}


def reseal(packet):
    packet['identity'] = w.canonical_identity(packet)
    return packet


def literal(op, value):
    return {'formal/term': 1, 'op': op, 'sort': [op], 'args': [], 'data': value}


class WitnessChecks(unittest.TestCase):
    def test_every_original_witness_including_both_native_backends_is_checked(self):
        accepted = []
        for name in PACKETS:
            with self.subTest(name=name):
                result = w.run(E / 'examples' / (name + '.json'), OUTPUT / name)
                self.assertEqual(result['status'], 'checked-term-satisfiability')
                self.assertTrue(all(set(v) <= {'propext', 'Quot.sound'} for v in result['axioms'].values()))
                self.assertEqual(result['backend_attestation'], 'not-established')
                self.assertFalse(result['compiler_proof_authority'])
                accepted.append({'id': name, **result})
        self.assertEqual(len(accepted), 32)
        (OUTPUT / 'accepted.json').write_text(json.dumps(accepted, indent=2) + '\n')

    def test_false_undefined_and_wrong_selected_values_are_rejected_by_lean(self):
        cases = {}
        packet = copy.deepcopy(PACKETS['constant']); packet['assertions'] = [literal('bool', False)]
        cases['false-assertion'] = packet
        packet = copy.deepcopy(PACKETS['integer']); packet['bindings'][0][2] = 8
        cases['wrong-concrete-value'] = packet
        packet = copy.deepcopy(PACKETS['variable-division']); packet['bindings'][1][2] = 0
        cases['zero-divisor'] = packet
        packet = copy.deepcopy(PACKETS['selected-dead-arm'])
        next(row for row in packet['bindings'] if row[0] == 'witness.p')[2] = True
        cases['selected-undefined-arm'] = packet
        packet = copy.deepcopy(PACKETS['nonlinear']); packet['bindings'][0][2] = 5
        cases['wrong-nonlinear-product'] = packet
        packet = copy.deepcopy(PACKETS['twenty-booleans']); packet['bindings'][-1][2] = False
        cases['last-of-twenty-booleans'] = packet
        rejected = []
        for name, packet in cases.items():
            with self.subTest(name=name):
                reseal(packet); w.validate(packet)
                target = OUTPUT / 'rejected' / name; target.mkdir(parents=True, exist_ok=True)
                path = target / 'packet.json'; path.write_text(json.dumps(packet) + '\n')
                # Seed an old success to test that a later failing run removes it.
                (target / 'Check.olean').write_bytes(b'stale-success')
                with self.assertRaisesRegex(ValueError, 'Lean did not accept'):
                    w.run(path, target)
                self.assertFalse((target / 'Check.olean').exists())
                self.assertTrue((target / 'lean.txt').exists())
                rejected.append({'id': name, 'packet': packet['identity'], 'status': 'rejected-by-lean'})
        (OUTPUT / 'rejected.json').write_text(json.dumps(rejected, indent=2) + '\n')

    def test_closed_schema_and_typed_binding_coverage(self):
        attacks = []
        for key, value in [('profile', 'invented'), ('mode', 'prove'), ('completion', 'implicit'), ('extra', True)]:
            packet = copy.deepcopy(PACKETS['integer']); packet[key] = value; attacks.append(packet)
        packet = copy.deepcopy(PACKETS['integer']); packet['bindings'] = []; attacks.append(packet)
        packet = copy.deepcopy(PACKETS['integer']); packet['bindings'] *= 2; attacks.append(packet)
        packet = copy.deepcopy(PACKETS['integer']); packet['bindings'][0][2] = True; attacks.append(packet)
        packet = copy.deepcopy(PACKETS['boolean']); packet['bindings'][0][2] = 0; attacks.append(packet)
        packet = copy.deepcopy(PACKETS['integer']); packet['bindings'][0][1] = ['bool']; attacks.append(packet)
        packet = copy.deepcopy(PACKETS['integer']); packet['bindings'].append(['observer.only', ['int'], 1]); attacks.append(packet)
        for packet in attacks:
            with self.assertRaises(ValueError):
                w.validate(reseal(packet))

    def test_generated_terms_values_and_names_are_independently_checked(self):
        for packet in PACKETS.values():
            integers, booleans = w.validate(packet)
            text = w.source(packet, integers, booleans)
            w.verify_source(text, packet, integers, booleans)
            for name in integers + booleans:
                self.assertNotIn(name, text)
        packet = PACKETS['integer']; integers, booleans = w.validate(packet)
        text = w.source(packet, integers, booleans)
        for changed in [text.replace('(Witness.mk [7]', '(Witness.mk [8]'),
                        text.replace('(Term.inputInt 0)', '(Term.inputInt 1)'),
                        text.replace('by decide', 'by sorry'), text + '\naxiom forged : False\n']:
            with self.assertRaises(ValueError):
                w.verify_source(changed, packet, integers, booleans)
        packet = PACKETS['boolean']; integers, booleans = w.validate(packet)
        with self.assertRaises(ValueError):
            w.verify_source(w.source(packet, integers, booleans).replace('[false]', '[true]'), packet, integers, booleans)

    def test_packet_hash_alone_does_not_connect_a_different_full_query(self):
        packet = copy.deepcopy(PACKETS['integer']); old = packet['identity']
        packet['question'] = '0' * 64
        reseal(packet)
        self.assertNotEqual(old, packet['identity'])
        # A declared original-tree theorem is valid on its own. Full-query
        # attribution requires the separate fresh BL reconstruction.
        w.validate(packet)
        self.assertEqual(packet['question'], '0' * 64)


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    unittest.main()
