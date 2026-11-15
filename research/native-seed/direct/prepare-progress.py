#!/usr/bin/env python3
"""Prepend an observational counter thread to an existing owned bundle.

Writes bytes only. Launches no ELF/VM/compiler; never parses Source or ANF.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bundle', type=Path, required=True,
                    help='existing guarded Sourceproof + exact original bundle bytes')
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
source = args.bundle.resolve()
output = args.out.resolve()
if output == source or output.exists():
    parser.error('choose a fresh diagnostic bundle path; original/prior observations are preserved')
helper = Path(__file__).with_name('progress-observer.scm')
prefix, original = helper.read_bytes(), source.read_bytes()
data = prefix + b'\n' + original
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(data)
assert output.read_bytes()[len(prefix) + 1:] == original
receipt = {'schema': 'bl.native.counter-observation-bundle', 'version': 1,
           'status': 'prepared-not-executed', 'qualification': False,
           'source': {'path': str(source), 'sha256': sha(original)},
           'observer': {'path': str(helper.resolve()), 'sha256': sha(prefix)},
           'generator': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())},
           'output': {'path': str(output), 'sha256': sha(data)},
           'original_suffix_byte_equal': True, 'prefix_bytes': len(prefix),
           'interval_seconds': 15, 'samples': 2,
           'changed_eligibility_hooks': False, 'source_or_anf_interpreter': False,
           'scope': 'approximate counters and exact live I/O-leaf phase only; scheduling/I/O overhead'}
output.with_suffix(output.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt['output']))
