#!/usr/bin/env python3
"""Bind a warm compiler-core observation; starts no VM, compiler or native ELF."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def scheme_string(value):
    return '"' + ''.join({'\\': '\\\\', '"': '\\"', '\n': '\\n', '\r': '\\r',
                          '\t': '\\t'}.get(c, '\\x' + format(ord(c), 'x') + ';'
                                           if ord(c) < 32 or ord(c) == 127 else c)
                         for c in value) + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = next(p for p in here.parents
                if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    compiler = base / 'out/compiler-native-owner'
    out = args.out.resolve()
    if out.exists():
        parser.error('select a fresh output directory')
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = digest(path)
        if expected is not None and actual != expected:
            raise RuntimeError('changed benchmark input: ' + str(path))
        inputs[str(path)] = actual
        return actual

    bind(__file__)
    receipt_path = compiler / 'full-native-build.json'
    bind(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('schema') != 'bl.native.full-bounded-build'
            or receipt.get('version') != 1 or receipt.get('status') != 'qualified'
            or receipt.get('compile_deadline_seconds') != 120):
        raise RuntimeError('requires original bounded native qualification')
    for path, expected in receipt['inputs'].items():
        selected = Path(path)
        bind(selected if selected.is_absolute() else base / selected, expected)
    first = next(row for row in receipt['builds'] if row['stage'] == 'stage1')
    image, source, bundle, host = (compiler / name for name in
                                  ('stage1', 'stage1.scm', 'bundle.scm', 'host.scm'))
    bind(image, first['executable_sha256'])
    bind(source, first['source_sha256'])
    bind(bundle)
    bind(host, 'd00c0c75a33cc4afc90315620d3039c48ed31464fdc0c32e5ac2841aa9d1ab8a')
    with image.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            raise RuntimeError('qualified stage1 is not a native ELF')
    pin_path = base / 'sdk-pin.json'
    bind(pin_path)
    pin = json.loads(pin_path.read_text())
    descriptor = Path(pin['sdk']) / 'artifact.json'
    bind(descriptor, pin['descriptor_sha256'])
    if json.loads(descriptor.read_text())['source'] != pin['source']:
        raise RuntimeError('SDK Source selection differs')
    # This binds the BEAM-side frontend to the ORIGINAL native compiler Source,
    # rather than silently benchmarking a later development compiler.
    identity_path = compiler / 'identity.json'
    bind(identity_path)
    identity = json.loads(identity_path.read_text())
    frontend_paths = {
        'priv/boot/anf.bl', 'priv/boot/compiler.bl', 'priv/boot/core.bl',
        'priv/boot/diag.bl', 'priv/boot/reader-node.bl', 'priv/boot/reader.bl',
        'priv/boot/rt.bl', 'priv/boot/server-clause.bl', 'priv/boot/sugar.bl',
        'priv/compat/clojure/core_ext.bl', 'priv/compat/clojure/re.bl',
        'priv/compat/clojure/string.bl', 'priv/host/compiler_data.bl',
        'priv/host/form_meta.bl', 'priv/host/meta.bl'}
    selected_paths = set()
    for row in identity['providers']:
        if row['path'] in frontend_paths:
            bind(Path(pin['source']) / row['path'], row['sha256'])
            selected_paths.add(row['path'])
    if selected_paths != frontend_paths:
        raise RuntimeError('original compiler closure lacks selected frontend Source')
    export_path = compiler / 'chunk-export.json'
    bind(export_path)
    exported = json.loads(export_path.read_text())
    bind(base / 'src/native/scheme.bl', exported['emission_inputs']['emitter_sha256'])
    bind(base / 'run')
    for name in ('compiler-values.bl', 'beam-benchmark.bl', 'native-observer.scm.in',
                 'compare-benchmark.py'):
        bind(here / name)
    fixture = here / 'compiler-values.bl'
    observer = (here / 'native-observer.scm.in').read_text()
    observer = observer.replace('@SOURCE@', scheme_string(fixture.read_text()))
    observer = observer.replace('@OUTPUT@', scheme_string(str(out / 'native.scm')))
    if '@SOURCE@' in observer or '@OUTPUT@' in observer:
        raise RuntimeError('unresolved observer DATA placeholder')
    out.mkdir(parents=True)
    prefix = observer.encode()
    original = bundle.read_bytes()
    observed = out / 'observer-bundle.scm'
    observed.write_bytes(prefix + b'\n' + original)
    result = {
        'schema': 'bl.native.warm-core-benchmark-preparation', 'version': 1,
        'status': 'prepared-not-executed', 'qualification': False,
        'scope': 'six macro-free Source function values; warm frontend :js ANF and Scheme text only',
        'inputs': inputs,
        'sdk': pin,
        'native': {'argv': [str(image), '--eval', str(observed), str(bundle)],
                   'runtime_deadline_seconds': 90,
                   'original_bundle_suffix_byte_equal':
                    observed.read_bytes()[len(prefix) + 1:] == original,
                   'observer': {'path': str(observed), 'sha256': digest(observed)}},
        'beam': {'argv': [str(base / 'run'), 'run', str(here / 'beam-benchmark.bl'),
                          str(fixture), str(out / 'beam.scm')],
                 'runtime_deadline_seconds': 240, 'vm_count': 1},
        'protocol': {'namespace': 'user', 'target': 'js',
                     'file_attribution': 'native-devtool-benchmark.bl',
                     'warmup_per_phase': 3, 'samples': 9, 'repetitions': 20,
                     'phases': ['read', 'compile', 'emit', 'pipeline'],
                     'parse_cache': 'none', 'anf_cache': 'none', 'emission_cache': 'none',
                     'clock_native': 'pinned Gambit ##get-monotonic-time! ticks / ##get-monotonic-time-frequency!',
                     'clock_beam': 'erlang monotonic nanoseconds',
                     'allocation_metric': None,
                     'excluded': ['process startup', 'Source file IO', 'macro installation',
                                  'macro execution', 'AOT planner', 'artifact admission',
                                  'Gambit frontend', 'C compilation', 'actor runtime']},
        'processes_launched_by_preparer': 0}
    (out / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'preparation': str(out / 'preparation.json'),
                      'native': result['native']['argv'], 'beam': result['beam']['argv']}))


if __name__ == '__main__':
    main()
