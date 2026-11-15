#!/usr/bin/env python3
"""Prepend a bounded continuation sampler; never execute an ELF/VM/compiler."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bundle', type=Path, required=True,
                    help='existing guarded proof plus original Source bundle DATA')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--delay', type=float, default=0.25)
parser.add_argument('--duration', type=float, default=2.0)
parser.add_argument('--interval', type=float, default=0.015)
parser.add_argument('--depth', type=int, default=24)
args = parser.parse_args()
for name in ('delay', 'duration', 'interval'):
    value = getattr(args, name)
    if not math.isfinite(value) or value < 0 or (name != 'delay' and value == 0):
        parser.error(name + ' must be a finite valid number of seconds')
if args.duration > 10 or args.interval < 0.005 or not 1 <= args.depth <= 64:
    parser.error('diagnostic bound: duration<=10, interval>=0.005, depth1..64')
source, output = args.bundle.resolve(), args.out.resolve()
if output == source or output.exists():
    parser.error('choose a fresh diagnostic output path')
template = Path(__file__).with_name('stack-observer.scm.in')
prefix = template.read_text()
for name in ('interval', 'duration', 'delay', 'depth'):
    prefix = prefix.replace('@' + name.upper() + '@', repr(getattr(args, name)))
if '@' in prefix:
    raise RuntimeError('unexpanded observer placeholder')
prefix, original = prefix.encode(), source.read_bytes()
data = prefix + b'\n' + original
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(data)
assert output.read_bytes()[len(prefix) + 1:] == original
receipt = {'schema': 'bl.native.continuation-sampling-bundle', 'version': 1,
           'status': 'prepared-not-executed', 'qualification': False,
           'source': {'path': str(source), 'sha256': sha(original)},
           'observer': {'path': str(template.resolve()), 'sha256': sha(template.read_bytes())},
           'generator': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())},
           'output': {'path': str(output), 'sha256': sha(data)},
           'original_suffix_byte_equal': True, 'prefix_bytes': len(prefix),
           'delay_seconds': args.delay, 'duration_seconds': args.duration,
           'interval_seconds': args.interval, 'max_interesting_frames': args.depth,
           'hook_or_step_replacements': False, 'source_or_anf_interpreter': False,
           'scope': 'Gambit safe-point-biased continuation samples; diagnostic only; not native CPU percentages'}
output.with_suffix(output.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt['output']))
