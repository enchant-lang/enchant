#!/usr/bin/env python3
"""Prepare the warm-core benchmark for a freshly built stage-1 compiler.

Same protocol and observer as benchmark/prepare-benchmark.py, but bound to the
selected build directory (stage1, bundle.scm, host.scm, stage1.scm) instead of
the original qualified compiler. Starts no VM. compare-benchmark.py consumes
the resulting preparation.json unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scheme_string(value):
    return '"' + ''.join({'\\': '\\\\', '"': '\\"', '\n': '\\n', '\r': '\\r',
                          '\t': '\\t'}.get(c, '\\x' + format(ord(c), 'x') + ';'
                                           if ord(c) < 32 or ord(c) == 127 else c)
                         for c in value) + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True, help='directory holding stage1 and bundle.scm')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[2]
    bench = base / 'benchmark'
    build, out = args.build.resolve(), args.out.resolve()
    if out.exists():
        parser.error('select a fresh output directory')
    image, bundle = build / 'stage1', build / 'bundle.scm'
    with image.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            raise RuntimeError('stage1 is not a native ELF')
    fixture = bench / 'compiler-values.bl'
    observer = (bench / 'native-observer.scm.in').read_text()
    observer = observer.replace('@SOURCE@', scheme_string(fixture.read_text()))
    observer = observer.replace('@OUTPUT@', scheme_string(str(out / 'native.scm')))
    assert '@SOURCE@' not in observer and '@OUTPUT@' not in observer
    out.mkdir(parents=True)
    observed = out / 'observer-bundle.scm'
    observed.write_bytes(observer.encode() + b'\n' + bundle.read_bytes())
    inputs = {str(p): digest(p) for p in
              [Path(__file__).resolve(), image, bundle, build / 'host.scm', build / 'stage1.scm',
               base / 'src/native/scheme.bl', base / 'sdk-pin.json', base / 'run',
               fixture, bench / 'beam-benchmark.bl', bench / 'native-observer.scm.in',
               bench / 'compare-benchmark.py']}
    result = {
        'schema': 'bl.native.warm-core-benchmark-preparation', 'version': 1,
        'status': 'prepared-not-executed', 'qualification': False,
        'scope': 'six macro-free Source function values; warm frontend :js ANF and Scheme text only',
        'inputs': inputs,
        'native': {'argv': [str(image), '--eval', str(observed), str(bundle)],
                   'observer': {'path': str(observed), 'sha256': digest(observed)}},
        'beam': {'argv': [str(base / 'run'), 'run', str(bench / 'beam-benchmark.bl'), '--',
                          str(fixture), str(out / 'beam.scm')]},
        'protocol': {'namespace': 'user', 'target': 'js', 'warmup_per_phase': 3, 'samples': 9,
                     'repetitions': 20, 'phases': ['read', 'compile', 'emit', 'pipeline'],
                     'excluded': ['process startup', 'Source file IO', 'macro installation',
                                  'Gambit frontend', 'C compilation', 'actor runtime']}}
    (out / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'native': result['native']['argv'], 'beam': result['beam']['argv']}))


if __name__ == '__main__':
    main()
