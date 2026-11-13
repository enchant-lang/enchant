"""Shared exact-value cases for future BEAM and JS semantic qualification.

Integer/Decimal payloads are strings and Floats are IEEE bits. JSON numbers
never carry an integer that could round at a target boundary. Expected results
come from Python's rational arithmetic, independently of either BL runtime.
"""
from fractions import Fraction
import json
from pathlib import Path
import struct
import sys


def integer(name, value):
    return {'id': name, 'kind': 'integer', 'digits': str(value)}


def decimal(name, coefficient, scale):
    return {'id': name, 'kind': 'decimal', 'coefficient': str(coefficient), 'scale': scale}


def floating(name, value):
    return {'id': name, 'kind': 'float', 'bits': struct.pack('>d', value).hex()}


values = [integer('int-zero', 0), floating('positive-zero', 0.0), floating('negative-zero', -0.0),
          decimal('decimal-zero', 0, 0), decimal('decimal-zero-scale-two', 0, 2),
          integer('int-one', 1), floating('float-one', 1.0), decimal('decimal-one', 1, 0),
          decimal('decimal-one-scale-two', 100, 2), floating('float-one-and-half', 1.5),
          decimal('decimal-one-and-half', 15, 1), decimal('decimal-one-and-half-scale-two', 150, 2),
          floating('float-tenth', 0.1), decimal('decimal-tenth', 1, 1),
          floating('float-half', 0.5), decimal('decimal-half-scale-two', 50, 2),
          integer('int-two-to-53', 2**53), floating('float-two-to-53', 2**53),
          integer('int-above-two-to-53', 2**53 + 1), integer('negative-int-below-two-to-53', -(2**53 + 1)),
          decimal('decimal-exact-float-tenth', 3602879701896397 * 5**55, 55),
          floating('minimum-subnormal', float.fromhex('0x0.0000000000001p-1022')),
          decimal('decimal-minimum-subnormal', 5**1074, 1074), decimal('decimal-below-minimum-subnormal', 1, 324),
          floating('negative-minimum-subnormal', -float.fromhex('0x0.0000000000001p-1022')),
          decimal('decimal-negative-minimum-subnormal', -(5**1074), 1074),
          floating('minimum-normal', float.fromhex('0x1.0p-1022')),
          floating('maximum-finite', float.fromhex('0x1.fffffffffffffp+1023')),
          decimal('decimal-maximum-finite', (2**53 - 1) * 2**971, 0),
          decimal('decimal-above-maximum-finite', (2**53 - 1) * 2**971 + 1, 0)]


def rational(value):
    kind = value['kind']
    if kind == 'integer':
        return Fraction(int(value['digits']))
    if kind == 'decimal':
        return Fraction(int(value['coefficient']), 10**value['scale'])
    actual = struct.unpack('>d', bytes.fromhex(value['bits']))[0]
    return Fraction.from_float(actual)


ratios = {value['id']: rational(value) for value in values}
pairs = []
for left in values:
    for right in values:
        a, b = ratios[left['id']], ratios[right['id']]
        pairs.append({'left': left['id'], 'right': right['id'], 'equal': a == b,
                      'compare': (a > b) - (a < b)})
data = {'schema': 'bl.proposed-finite-exact-numeric-cases.v1',
        'profile': 'proposed-finite-exact-numeric-v1', 'values': values, 'pairs': pairs,
        'scope': 'Finite exact-value test vectors. Raw collection key identity, nonfinite values and compiler preservation are separate qualifications.',
        'oracle': 'Python fractions.Fraction; Float values decoded from committed binary64 bits.',
        'qualified_runtime': False, 'compiler_proof_authority': False}
body = json.dumps(data, indent=2) + '\n'
output = Path(__file__).with_name('finite-number-cases.json')
if sys.argv[1:] == ['--check']:
    assert output.read_text() == body
    print(json.dumps({'status': 'unchanged', 'values': len(values), 'pairs': len(pairs)}))
else:
    assert not sys.argv[1:]
    output.write_text(body)
    print(json.dumps({'status': 'generated', 'values': len(values), 'pairs': len(pairs)}))
