"""Relink one qualified stage two with different C flags on its runtime units."""
import argparse
import json
import os
import statistics
import subprocess
from pathlib import Path

from run import HERE, IMAGE, QUAL, command, sha, write


def run(pipeline, out):
    out.mkdir()
    reference = json.loads((pipeline / 'pipeline.json').read_text())
    qualification = json.loads(QUAL.read_text())
    expected = qualification['images']['stage2']
    sha(IMAGE / 'stage2', expected)
    sha(IMAGE / 'eval-prepared.scm', qualification['prepared_macro_bundle_sha256'])
    sha(pipeline / 'reader.bl', reference['source_sha256'])
    build = json.loads((IMAGE / 'full-native-build.json').read_text())
    stage = next(row for row in build['builds'] if row['stage'] == 'stage2')
    manifest = Path(stage['split_manifest'])
    sha(manifest, stage['split_manifest_sha256'])
    link = next(row['argv'] for row in build['runs'] if row['label'] == 'stage2-native-link')
    report = dict(image=expected, fixture=reference['source_sha256'], objects=[], runs=[])
    args = list(link)
    args[-1] = str(out / 'original')
    subprocess.run(args, check=True)
    sha(args[-1], expected)
    for unit in stage['units'][:2]:
        path = manifest.parent / unit['file']
        sha(path, unit['sha256'])
        if '(define v_' in path.read_text():
            raise ValueError('Expected host-only Scheme units')
        sha(unit['object'], unit['object_sha256'])
        sha(unit['c'], unit['c_sha256'])
        flags = list(unit['c_flags'])
        if flags[0] != '-O0':
            raise ValueError('Expected unoptimized baseline')
        flags[0] = '-O1'
        obj = out / (path.stem + '.o')
        command([link[0], *flags, '-c', unit['c'], '-o', obj], os.environ,
                out / (path.stem + '.log'), timeout=1800)
        report['objects'].append(dict(unit=unit['ordinal'], c_sha=sha(unit['c']),
                                      original=unit['object_sha256'], optimized=sha(obj)))
        args[args.index(unit['object'])] = str(obj)
    args[-1] = str(out / 'host-O1')
    subprocess.run(args, check=True)
    report['candidate'] = sha(args[-1])
    observer = (pipeline / 'observer.scm').read_text().replace(
        json.dumps(str(pipeline)), json.dumps(str(out)))
    marker = '(define (A-run)'
    observer = observer.replace(marker, (HERE / 'cost-phases.scm').read_text() + '\n' + marker)
    (out / 'observer.scm').write_text(observer)
    output = reference['runs'][0]['emitted_sha256']
    for name in ['original', 'host-O1', 'host-O1', 'original']:
        log = command([out / name, '--eval', out / 'observer.scm', IMAGE / 'eval-prepared.scm'],
                      os.environ, out / f'{len(report["runs"])}.log', timeout=180)
        rows = [line.split() for line in log.splitlines() if line.startswith('COST ')]
        if [row[1] for row in rows] != ['read', 'compile', 'emit'] * 4 or 'emit-failures 0' not in log:
            raise ValueError('Incomplete or refused job')
        report['runs'].append(dict(arm=name, output=sha(out / 'native.scm', output),
            wall_ms=[float(row[2])*1000 for row in rows],
            cpu_ms=[(float(row[3])+float(row[4]))*1000 for row in rows]))
    write(out / 'runtime-flags.json', report)
    for name in ['original', 'host-O1']:
        cpu = [v for row in report['runs'] if row['arm'] == name for v in row['cpu_ms']]
        print(name, [statistics.median(cpu[i::3]) for i in range(3)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pipeline', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    options = parser.parse_args()
    run(options.pipeline.resolve(), options.out.resolve())
