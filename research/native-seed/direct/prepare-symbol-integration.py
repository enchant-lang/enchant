#!/usr/bin/env python3
"""Prepare fixed dispatch work for a NEW compiled host; execute nothing."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bundle', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--iterations', type=int, default=1000,
                    help='fixed actual C calls, 0 skips timed work; same value in both modes')
args = parser.parse_args()
if not 0 <= args.iterations <= 100000:
    parser.error('iterations must be0..100000')
original_path, output = args.bundle.resolve(), args.out.resolve()
if output.exists() or output == original_path:
    parser.error('choose a fresh diagnostic output path')
template = Path(__file__).with_name('symbol-integration.scm.in')
prefix = template.read_text().replace('@ITERATIONS@', str(args.iterations)).encode()
original = original_path.read_bytes()
data = prefix + b'\n' + original
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(data)
assert output.read_bytes()[len(prefix) + 1:] == original
receipt = {'schema': 'bl.native.symbolic-MFA-dispatch-diagnostic', 'version': 1,
           'status': 'prepared-not-executed', 'qualification': False,
           'source': {'path': str(original_path), 'sha256': sha(original)},
           'template': {'path': str(template.resolve()), 'sha256': sha(template.read_bytes())},
           'generator': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())},
           'output': {'path': str(output), 'sha256': sha(data)},
           'original_suffix_byte_equal': True, 'prefix_bytes': len(prefix),
           'fixed_actual_C_calls': args.iterations, 'strict_integration_checks': 17,
           'requires_new_compiled_host': True, 'installs_host_adapters': False,
           'source_or_anf_interpreter': False,
           'mode_environment': 'BL_NATIVE_C_SYMBOL_MFAS',
           'scope': 'published C export dispatch and same-image wall-time diagnostic only; exits before macro Source'}
output.with_suffix(output.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt['output']))
