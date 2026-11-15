#!/usr/bin/env python3
"""Prepare an observational GSI load transport for an exact built C image.

Starts no compiler or runtime. Source bodies are unchanged compiled C objects;
only the final command-line entry becomes explicit identical --eval arguments.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--eval-bundle', type=Path, required=True,
                        help='exact proof Source bundle used by the prior standalone --eval command')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--interval', type=int, default=100000)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error('--interval must be positive')
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    plan, out = args.plan.resolve(), args.out.resolve()
    bundle, source = args.eval_bundle.resolve(), args.source.resolve()
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        digest = sha(path)
        if expected is not None and expected != digest:
            raise RuntimeError('observational input identity changed: ' + str(path))
        inputs[str(path)] = digest
        return path

    bind(here)
    template_path = bind(here.with_name('observer.scm'))
    bind(bundle)
    bind(source)
    receipt_path = bind(plan / 'build-evidence.json')
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('schema') != 'bl.native.direct-unit-build'
            or receipt.get('status') != 'built-not-executed'
            or receipt.get('action-abi') != 2 or receipt.get('header-action-abi') != 2
            or receipt.get('compiler_run') is not False):
        raise RuntimeError('observer requires the actual previously built bounded C image')
    for path, expected in receipt['inputs'].items():
        bind(path, expected)
    rows = bind(plan / 'index.tsv').read_text().splitlines()
    if len(rows) < 2 or rows[0] != 'BL_NATIVE_DIRECT_UNITS\t1\t32' or rows[1] != 'B\t2':
        raise RuntimeError('observer requires the exact bounded C index')
    units = []
    for text in rows[2:]:
        row = text.split('\t')
        if row[0] in ('H', 'M', 'E', 'A', 'P'):
            bind(plan / row[1], row[2])
        elif row[0] == 'U':
            units.append({'name': row[2], 'phase': row[1]})
            bind(plan / row[3], row[4])
            bind(plan / row[5], row[6])
    if [r['name'] for r in receipt['objects']] != ['host', *[r['name'] for r in units]]:
        raise RuntimeError('compiled object list differs from the unchanged unit index')
    for record in receipt['objects']:
        bind(plan / (record['name'] + '.o1'), record['sha256'])
    bind(plan / 'compiler', receipt['executable']['sha256'])
    metadata = (plan / 'metadata.scm').read_text()
    exact_entry = '(native-main (native-command-line))\n'
    header = (';; Direct C compiler: relative link entries; unit root is explicit.\n'
              '(define native-direct-unit-root (getenv "BL_NATIVE_C_UNIT_ROOT" #f))\n'
              '(if (not native-direct-unit-root) (error "BL_NATIVE_C_UNIT_ROOT is required"))\n')
    host_load = '(load (string-append native-direct-unit-root "/host.o1"))\n(native-c-require-action-abi! 2)\n'
    metadata_load = '(native-install-bundle! ' + metadata + ')\n(set! native-c-backend (bl-key "c"))\n'
    unit_load = lambda unit: '(load (string-append native-direct-unit-root "/' + unit['name'] + '.o1"))\n'
    exact = header + host_load + metadata_load + ''.join(map(unit_load, units)) + exact_entry
    if (plan / 'assembly.scm').read_text() != exact or (plan / 'entry.scm').read_text() != exact_entry:
        raise RuntimeError('compiled image assembly/entry is not the canonical exact sequence')
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'driver.scm').exists() or (out / 'preparation.json').exists():
        raise RuntimeError('choose a fresh observational output directory')
    q = lambda text: json.dumps(str(text), ensure_ascii=False)
    log = lambda event: '(display ' + q('DIRECT_OBSERVER_' + event + '\n') + ') (force-output)\n'
    hooks = template_path.read_text().replace('@INTERVAL@', str(args.interval))
    program = log('BEGIN') + header + log('BEFORE_HOST') + host_load + log('AFTER_HOST')
    program += hooks + '\n' + log('BEFORE_METADATA') + metadata_load + log('AFTER_METADATA')
    for unit in units:
        label = unit['name'] + '_' + unit['phase']
        program += log('BEFORE_UNIT_' + label) + unit_load(unit) + log('AFTER_UNIT_' + label)
    command = ['--eval', str(bundle), str(source)]
    program += log('BEFORE_MAIN')
    program += '(native-main (list ' + ' '.join(map(q, command)) + '))\n' + log('AFTER_MAIN')
    driver = out / 'driver.scm'
    driver.write_text(program)
    tools = json.loads(bind(root / 'research/native-seed/toolchain-pin.json').read_text())
    gsi = bind(Path(tools['gambit']) / 'bin/gsi')
    for name, expected in inputs.items():
        if sha(name) != expected:
            raise RuntimeError('observer input changed during preparation: ' + name)
    report = {'schema': 'bl.native.direct-source-observer', 'version': 1,
              'status': 'prepared-not-executed-not-qualified', 'inputs': inputs,
              'driver': {'path': str(driver), 'sha256': sha(driver)},
              'original_assembly_sha256': sha(plan / 'assembly.scm'),
              'same_compiled_host_and_all_units': True, 'metadata_bytes_unchanged': True,
              'source_file_bytes_unchanged': True, 'authored_source_scheme_fallback': False,
              'replacement_entry_args': command, 'observations_only': True,
              'interval': args.interval, 'objects': receipt['objects'],
              'argv': [str(gsi), str(driver)], 'environment': {'BL_NATIVE_C_UNIT_ROOT': str(plan)}}
    (out / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('env BL_NATIVE_C_UNIT_ROOT=' + shlex.quote(str(plan)) + ' '
          + shlex.join([str(gsi), str(driver)]))


if __name__ == '__main__':
    main()
