#!/usr/bin/env python3
"""Prepare one typed equality-call observation atop the admitted original benchmark; starts no process."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = next(p for p in here.parents
                if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    benchmark_preparer = base / 'benchmark/prepare-benchmark.py'
    spec = importlib.util.spec_from_file_location('profile_preparation_literals', benchmark_preparer)
    literals = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(literals)
    preparation = args.preparation.resolve()
    parent = json.loads(preparation.read_text())
    if parent['schema'] != 'bl.native.warm-core-benchmark-preparation':
        raise ValueError('requires admitted warm-core benchmark preparation')
    inputs = dict(parent['inputs'])
    inputs[str(preparation)] = sha(preparation)
    for path, expected in inputs.items():
        if sha(path) != expected:
            raise ValueError('profile input changed: ' + path)
    native = parent['native']
    observer = native['observer']
    if sha(observer['path']) != observer['sha256']:
        raise ValueError('original benchmark observer changed')
    inputs[str(Path(observer['path']).resolve())] = observer['sha256']
    inputs[str(benchmark_preparer)] = sha(benchmark_preparer)
    inputs[str(Path(__file__).resolve())] = sha(__file__)
    template = here / 'arguments.scm.in'
    inputs[str(template)] = sha(template)
    original = Path(native['argv'][3]).read_bytes()
    observed = Path(observer['path']).read_bytes()
    if not observed.endswith(b'\n' + original):
        raise ValueError('owned original bundle suffix differs')
    prefix = observed[:-len(original)-1].decode()
    marker = '(define (bench-run)\n'
    if prefix.count(marker) != 1:
        raise ValueError('unexpected benchmark entrypoint')
    prefix = prefix.split(marker)[0]
    out = args.out.resolve()
    if out.exists():
        raise ValueError('select a fresh profile output directory')
    body = template.read_text().replace('@OUTPUT@', literals.scheme_string(str(out / 'native.scm')))
    out.mkdir(parents=True)
    observation = out / 'profile-bundle.scm'
    observation.write_bytes((prefix + body).encode() + b'\n' + original)
    result = {'schema': 'bl.native.equality-argument-count-preparation', 'version': 1,
              'status': 'prepared-not-executed', 'qualification': False,
              'scope': 'one real Reader parse; actual original rt/k-eqv and k-compare argument classes; counts only',
              'inputs': inputs, 'phases': ['compiled-call-control', 'one-read'], 'warmup_reads': 3, 'measured_reads': 1,
              'instrumentation': 'registry-slot observation wrappers invoke original compiled native procedures; separate Gambit tables',
              'timing_claim': False,
              'original_bundle_suffix_byte_equal': observation.read_bytes().endswith(b'\n' + original),
              'observer': {'path': str(observation), 'sha256': sha(observation)},
              'argv': [native['argv'][0], '--eval', str(observation), native['argv'][3]],
              'runtime_deadline_seconds': 30, 'processes_launched_by_preparer': 0}
    (out / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'preparation': str(out / 'preparation.json'), 'argv': result['argv']}))


if __name__ == '__main__':
    main()
