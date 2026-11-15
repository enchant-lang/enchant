#!/usr/bin/env python3
"""Copy an admitted semantic plan to a fresh output; never execute its code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    source, target = args.source.resolve(), args.target.resolve()
    if source == target or source in target.parents or target in source.parents:
        raise RuntimeError('derived plan must have a disjoint fresh output directory')
    if target.exists() and any(target.iterdir()):
        raise RuntimeError('derived output already contains files')
    report_path = source / 'build-evidence.json'
    report = json.loads(report_path.read_text())
    if (report.get('schema') != 'bl.native.direct-unit-build'
            or report.get('version') != 1 or report.get('action-abi') != 2
            or report.get('header-action-abi') != 2 or report.get('status') != 'built-not-executed'
            or report.get('compiler_run') is not False
            or report.get('inputs') != report.get('inputs_after')):
        raise RuntimeError('source plan lacks an unchanged successful build receipt')
    index = source / 'index.tsv'
    rows = index.read_text(encoding='ascii').splitlines()
    if len(rows) < 2 or rows[0] != 'BL_NATIVE_DIRECT_UNITS\t1\t32' or rows[1] != 'B\t2':
        raise RuntimeError('unsupported source plan schema')
    files = {'index.tsv', 'bundle.scm'}
    for line in rows[2:]:
        fields = line.split('\t')
        if fields[0] in ('H', 'M', 'E', 'A', 'P'):
            candidates = [(fields[1], fields[2])]
        elif fields[0] == 'U':
            candidates = [(fields[3], fields[4]), (fields[5], fields[6])]
        else:
            continue
        for name, expected in candidates:
            if (not re.fullmatch(r'[a-z][a-z0-9.-]*', name)
                    or not re.fullmatch(r'[0-9a-f]{64}', expected)
                    or digest(source / name) != expected):
                raise RuntimeError('source semantic plan hash/name changed: ' + name)
            files.add(name)
    protected = {source / name for name in files}
    protected.add(report_path)
    protected.add(source / 'compiler')
    if digest(source / 'compiler') != report['executable']['sha256']:
        raise RuntimeError('source executable differs from build receipt')
    for row in report['objects']:
        obj = source / (row['name'] + '.o1')
        if digest(obj) != row['sha256']:
            raise RuntimeError('source object differs from receipt: ' + row['name'])
        protected.add(obj)
    before = {str(path): digest(path) for path in sorted(protected)}
    target.mkdir(parents=True, exist_ok=True)
    for name in sorted(files):
        shutil.copy2(source / name, target / name)
        if digest(target / name) != before[str(source / name)]:
            raise RuntimeError('derived plan copy differs: ' + name)
    shutil.copy2(report_path, target / 'source-build-evidence.json')
    if any(digest(Path(path)) != value for path, value in before.items()):
        raise RuntimeError('source plan changed while copying')
    receipt = {'schema': 'bl.native.direct-derived-host-plan', 'version': 1, 'action-abi': 2,
               'status': 'copied-not-built', 'source': str(source), 'target': str(target),
               'source_build': {'path': str(report_path), 'sha256': before[str(report_path)]},
               'semantic_files': {name: digest(target / name) for name in sorted(files)},
               'protected_source_artifacts': before,
               'source_parser': False, 'native_code_executed': False}
    (target / 'derived-plan.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('DERIVED_HOST_PLAN_COPIED ' + str(target))


if __name__ == '__main__':
    main()
