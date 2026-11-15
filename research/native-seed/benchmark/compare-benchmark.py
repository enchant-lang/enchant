#!/usr/bin/env python3
"""Compare already collected warm-core observations; starts no runtime."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


def observations(path):
    text = path.read_text()
    if text.count('BL_COMPILER_BENCHMARK_DONE') != 1:
        raise ValueError('benchmark did not finish exactly once: ' + str(path))
    result = {phase: {} for phase in ('read', 'compile', 'emit', 'pipeline')}
    for line in text.splitlines():
        if not line.startswith('BL_COMPILER_BENCHMARK '):
            continue
        tag, phase, sample, repetitions, elapsed = line.split()
        sample, repetitions, elapsed = int(sample), int(repetitions), float(elapsed)
        if (phase not in result or sample not in range(9) or repetitions != 20
                or not math.isfinite(elapsed) or elapsed <= 0 or sample in result[phase]):
            raise ValueError('invalid benchmark row: ' + line)
        result[phase][sample] = elapsed / repetitions
    if any(set(values) != set(range(9)) for values in result.values()):
        raise ValueError('incomplete benchmark samples: ' + str(path))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    preparation = json.loads((directory / 'preparation.json').read_text())
    if preparation['schema'] != 'bl.native.warm-core-benchmark-preparation':
        raise ValueError('unexpected benchmark preparation')
    for path, expected in preparation['inputs'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('benchmark input changed: ' + path)
    observer = preparation['native']['observer']
    if hashlib.sha256(Path(observer['path']).read_bytes()).hexdigest() != observer['sha256']:
        raise ValueError('native observer changed after preparation')
    native_source = (directory / 'native.scm').read_bytes()
    if not native_source or native_source != (directory / 'beam.scm').read_bytes():
        raise ValueError('selected Source did not produce identical Scheme bytes')
    native = observations(directory / 'native.log')
    beam = observations(directory / 'beam.log')
    phases = {}
    for phase in native:
        n, b = list(native[phase].values()), list(beam[phase].values())
        phases[phase] = {'native_seconds_per_operation': n,
                         'beam_seconds_per_operation': b,
                         'native_median_seconds': statistics.median(n),
                         'beam_median_seconds': statistics.median(b),
                         'beam_over_native_median_ratio': statistics.median(b) / statistics.median(n)}
    result = {'schema': 'bl.native.warm-core-benchmark-observation', 'version': 1,
              'qualification': False, 'scope': preparation['scope'],
              'scheme_byte_equal': True, 'scheme_sha256': hashlib.sha256(native_source).hexdigest(),
              'protocol': preparation['protocol'], 'phases': phases,
              'limits': ['small macro-free corpus', 'no edit-loop or AOT speed claim',
                         'native observation wrapper is interpreted Scheme; algorithms are compiled BL',
                         'no allocator equivalence or allocation metric asserted']}
    (directory / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({phase: value['beam_over_native_median_ratio']
                      for phase, value in phases.items()}))


if __name__ == '__main__':
    main()
