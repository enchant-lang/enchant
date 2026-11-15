#!/usr/bin/env python3
"""Prepare a GVM module probe against the qualified original host; no execution."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler-dir', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--large', type=int, default=100000)
parser.add_argument('--observer', type=Path, default=Path(__file__).with_name('check-tail.scm'))
args = parser.parse_args()
directory, output = args.compiler_dir.resolve(), args.out.resolve()
if output.exists() or not 2000 < args.large <= 1000000:
    parser.error('fresh output and a bounded larger tail count2001..1000000 required')
host, source, image, bundle = (directory / p for p in ['host.scm', 'stage1.scm', 'stage1', 'bundle.scm'])
receipt_path = directory / 'full-native-build.json'
qualified = json.loads(receipt_path.read_text())
if qualified.get('status') != 'qualified':
    raise RuntimeError('the original compiled host image must have its qualified receipt')
build = next(row for row in qualified['builds'] if row['stage'] == 'stage1')
if sha(host) != 'd00c0c75a33cc4afc90315620d3039c48ed31464fdc0c32e5ac2841aa9d1ab8a':
    raise RuntimeError('probe requires the exact original qualified host')
if sha(source) != build['source_sha256'] or sha(image) != build['executable_sha256']:
    raise RuntimeError('qualified host compiler source/image differs from the receipt')
template = args.observer.resolve()
prefix = template.read_text().replace('@LARGE@', str(args.large)).encode()
original = bundle.read_bytes()
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(prefix + b'\n' + original)
assert output.read_bytes()[len(prefix) + 1:] == original
receipt = {'schema': 'bl.native.gvm-original-host-tail-observer', 'version': 1,
           'status': 'prepared-not-executed', 'qualification': False,
           'inputs': {str(p): sha(p) for p in [host, source, image, bundle, receipt_path, template, Path(__file__).resolve()]},
           'output': {'path': str(output), 'sha256': sha(output)},
           'original_bundle_suffix_byte_equal': True,
           'native_module_environment': 'BL_GVM_PROBE_MODULE',
           'entry_argv': [str(image), '--eval', str(output), str(bundle)],
           'large_count': args.large, 'runtime_by_preparer': False,
           'scope': 'native GVM tail/publication/GC host integration; exits before macro Source; no full Source gate'}
output.with_suffix(output.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt['entry_argv']))
