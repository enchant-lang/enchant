#!/usr/bin/env python3
"""One actual native-GVM Source gate; no SDK, builds or fixpoint claim."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time


SOURCE_FIXTURE_SHA256 = '9201bb0d6635dc2050665cb532b4897c2a9b466472097a88a4991d4bfe1a99d2'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def scheme_string(value):
    escapes = {'\\': '\\\\', '"': '\\"', '\n': '\\n', '\r': '\\r', '\t': '\\t'}
    return '"' + ''.join(escapes.get(c, '\\x' + format(ord(c), 'x') + ';'
                       if ord(c) < 32 or ord(c) == 127 else c) for c in value) + '"'


def elf(path):
    with Path(path).open('rb') as stream:
        return stream.read(4) == b'\x7fELF'


def main():
    base = Path(__file__).resolve().parents[1]
    root = base.parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True, help='captured GVM compiler plan')
    parser.add_argument('--build', type=Path, required=True, help='build-profile.py output')
    parser.add_argument('--host-ledger', type=Path, required=True, help='exact host.components.scm')
    parser.add_argument('--route', choices=('c', 'llvm'), default='c')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    plan, built, ledger, out = (p.resolve() for p in
                               (args.plan, args.build, args.host_ledger, args.out))
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise RuntimeError('preserve prior observations; select an empty output directory')
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        if str(path) in inputs:
            if expected is not None and inputs[str(path)] != expected:
                raise RuntimeError('conflicting input identity: ' + str(path))
            return inputs[str(path)]
        actual = sha(path)
        if (expected is not None and actual != expected) or (
                str(path) in inputs and inputs[str(path)] != actual):
            raise RuntimeError('input differs: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def record(row):
        bind(row['path'], row['sha256'])
        return Path(row['path']).resolve()

    def cache_receipt(row):
        path = record(row)
        value = json.loads(path.read_text())
        for artifact, expected in value['artifacts'].items():
            bind(artifact, expected)
        return value

    def load_module(name, path):
        bind(path)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    decoder = load_module('owned_gvm_metadata', base / 'gvm/read-metadata.py')
    tree_helper = load_module('owned_native_tree', base / 'check-self-emission.py')
    build_path = built / 'build.json'
    bind(build_path)
    build = json.loads(build_path.read_text())
    if (build.get('schema') != 'bl.native.gvm-profile-build' or build.get('version') != 1
            or build.get('status') != 'compiled-not-qualified' or build.get('qualification') is not False
            or Path(build['plan']).resolve() != plan
            or build.get('child_deadline_seconds') != 120):
        raise RuntimeError('requires the exact completed GVM native profile build')
    for path, expected in build['inputs'].items():
        bind(path, expected)
    for name, expected in build['semantic_files'].items():
        if Path(name).name != name:
            raise RuntimeError('semantic artifact is not a plan-relative filename')
        bind(plan / name, expected)
    manifest = decoder.decode((plan / 'plan.manifest.scm').read_text())
    if (manifest.get('schema') != 'bl.native.gvm-compiler-units' or manifest.get('version') != 1
            or manifest.get('runtime-abi') != 1 or manifest.get('group-size') != 32
            or manifest.get('source-interpreter') is not False
            or manifest.get('authored-scheme-bodies') is not False
            or manifest.get('gvm-interpreter') is not False
            or manifest.get('c-lambda-stepper') is not False):
        raise RuntimeError('GVM plan contains an unadmitted executable representation')
    if (plan / 'plan.json').exists():
        bind(plan / 'plan.json')
        if json.loads((plan / 'plan.json').read_text()) != manifest:
            raise RuntimeError('SDK JSON differs from the native owned manifest')
    for key in ('metadata', 'assembly'):
        if bind(plan / (key + '.scm')) != manifest[key + '-sha256']:
            raise RuntimeError('GVM manifest fixed-artifact digest differs')
    if (plan / 'entry.scm').read_text() != '(native-main (native-command-line))\n':
        raise RuntimeError('GVM command entry differs')
    index = (plan / 'index.tsv').read_bytes()
    last = index.splitlines(keepends=True)
    if (not last or not last[-1].startswith(b'P\tplan.manifest.scm\t')
            or hashlib.sha256(b''.join(last[:-1])).hexdigest() != manifest['index-core-sha256']):
        raise RuntimeError('GVM semantic index core differs')
    host_ledger = decoder.decode(ledger.read_text())
    bind(ledger)
    if host_ledger != manifest['host'] or bind(plan / 'host.scm') != host_ledger['source-sha256']:
        raise RuntimeError('GVM host source/ledger differs from the selected plan')
    hrows = [line.decode().split('\t') for line in index.splitlines() if line.startswith(b'H\t')]
    if len(hrows) != 1 or hrows[0][3] != sha(ledger):
        raise RuntimeError('host ledger is not the canonical Source data projection')
    for name in ('source', 'c', 'llvm', 'receipt'):
        record(build['host'][name])
    for route in ('c', 'llvm'):
        if Path(build['host'][route]['path']).resolve() != built / route / 'host.o1':
            raise RuntimeError('host native module is outside the selected runtime root')
    cache_receipt(build['host']['receipt'])
    owners, exports, modules = [], [], []
    if len(build['modules']) != len(manifest['units']):
        raise RuntimeError('native module count differs from the captured GVM plan')
    for unit, module in zip(manifest['units'], build['modules']):
        if module['name'] != unit['name'] or module['module'] != unit['module']:
            raise RuntimeError('GVM module order differs')
        if Path(module['native']['path']).resolve() != built / 'c' / unit['object']:
            raise RuntimeError('C module is outside the selected runtime root')
        if Path(module['llvm']['path']).resolve() != built / 'llvm' / unit['object']:
            raise RuntimeError('LLVM module is outside the selected runtime root')
        for name in ('data', 'emission', 'build', 'receipt', 'c', 'native', 'llvm'):
            record(module[name])
        cache_receipt(module['receipt'])
        if sha(plan / unit['data']['path']) != unit['data']['sha256']:
            raise RuntimeError('captured GVM DATA differs')
        emission = decoder.decode((plan / unit['manifest']['path']).read_text())
        if (emission != unit['emission'] or emission['module'] != unit['module']
                or emission.get('runtime-abi') != 1 or emission.get('program-control') != 'native-gvm'
                or any(emission.get(flag) is not False for flag in
                    ('authored-scheme', 'source-interpreter', 'anf-interpreter',
                     'gvm-interpreter', 'c-lambda-stepper'))):
            raise RuntimeError('native GVM emission manifest differs')
        module_build = json.loads(Path(module['build']['path']).read_text())
        if (module_build.get('schema') != 'bl.native.gvm-module-build'
                or module_build.get('status') != 'compiled-not-qualified'
                or module_build.get('route') != 'both'
                or module_build.get('module_linker_name') != unit['object']
                or [j['name'] for j in module_build['jobs']] != ['import', 'c', 'llvm-ir', 'llvm-link']
                or any(j.get('returncode') != 0 for j in module_build['jobs'])):
            raise RuntimeError('GVM module lacks both successful native routes')
        for path, expected in module_build['inputs'].items():
            bind(path, expected)
        for path, expected in module_build['artifacts'].items():
            bind(path, expected['sha256'])
        for owner in emission['owner-globals']:
            if owner not in owners:
                owners.append(owner)
        exports.extend(emission.get('exports', []))
        modules.append(unit['module'])
    if (not owners or not exports or len(set(modules)) != len(modules)
            or len({row['global'] for row in exports}) != len(exports)):
        raise RuntimeError('GVM physical export/native owner inventory is incomplete')
    required = {('rt', 'k-first'), ('reader', 'read-string'), ('compiler', 'compile'),
                ('native.bootstrap', 'prepare'), ('native.eval', 'eval-form'),
                ('native.gvm-lower', 'emit-unit'), ('native.gvm-eval', 'eval-node'),
                ('native.gvm-units', 'write-plan!'), ('native.gvm-bootstrap', 'main')}
    if not required.issubset({(row['namespace'], row['name']) for row in exports}):
        raise RuntimeError('the nine actual Source/compiler/GVM exports are absent')
    image = record(build['executables'][args.route])
    if (image != built / args.route / 'compiler' or not elf(image)
            or not os.access(image, os.X_OK)):
        raise RuntimeError('selected GVM compiler is not the exact executable ELF')
    cache_receipt(build['entry']['receipt'])
    bundle = plan / 'bundle.scm'
    template = base / 'gvm/source-proof.scm.in'
    corpus = base / 'fixtures/compiler-source.bl'
    for path in (Path(__file__), bundle, template, corpus):
        bind(path)
    bind(corpus, SOURCE_FIXTURE_SHA256)
    captured = decoder.decode(bundle.read_text())
    if captured.get('schema') != 'bl.native.source-bundle':
        raise RuntimeError('Source gate requires the original owned Source bundle')
    captured_units = captured['units']
    if len(captured_units) != len(manifest['sources']):
        raise RuntimeError('Source bundle count differs from the captured GVM profile')
    for unit, source in zip(captured_units, manifest['sources']):
        if (unit['ns'] != source['namespace'] or unit['path'] != source['path']
                or hashlib.sha256(unit['source'].encode()).hexdigest() != source['sha256']):
            raise RuntimeError('original Source identity differs in the GVM bundle')
    q = scheme_string
    owner_data = '(' + ' '.join(q(owner) for owner in owners) + ')'
    export_data = '(' + ' '.join('(' + q(row['global']) + ' ' + str(row['arity']) +
                    ' ' + q(row['owner-global']) + ')' for row in exports) + ')'
    prefix = template.read_text().replace('@BUNDLE_PATH@', q(str(bundle))).replace(
        '@LEDGER_PATH@', q(str(ledger))).replace('@OWNER_GLOBALS@', owner_data).replace(
        '@EXPORT_ROWS@', export_data).encode()
    proof = out / 'source-proof-bundle.scm'
    original_bundle = bundle.read_bytes()
    proof.write_bytes(prefix + b'\n' + original_bundle)
    bind(proof)
    env = os.environ.copy()
    env['BL_NATIVE_GVM_UNIT_ROOT'] = str(built / args.route)
    for key in list(env):
        if key.startswith('BL_NATIVE_C_') or key in ('BL_NATIVE_TRACE', 'BL_NATIVE_GVM_GC_INTERVAL'):
            env.pop(key)
    argv = [str(image), '--eval', str(proof), str(corpus)]
    log = out / 'source.log'
    start, timed, cleanup = time.monotonic(), False, None
    with log.open('w') as stream:
        process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        tree = tree_helper.OwnedTree(process)
        try:
            while process.poll() is None:
                tree.discover()
                if time.monotonic() - start >= 120:
                    timed = True
                    break
                time.sleep(0.1)
        finally:
            cleanup = tree.cleanup()
    output = log.read_text(errors='replace')
    rows, dynamic = [], []
    witness_error = None
    try:
        rows = [json.loads(line.split(' ', 1)[1]) for line in output.splitlines()
                if line.startswith('NATIVE_GVM_DYNAMIC_WITNESS ')]
        seen_modules = set()
        for index, row in enumerate(rows, 1):
            if (row.get('backend') != 'gvm' or row.get('runtime_abi') != 1
                    or row.get('evaluations') != index or row.get('required_gvm_exports') != 9
                    or row.get('scheme_data_only') is not True or row.get('old_stepper') is not False
                    or any(type(row.get(name)) is not int or row[name] <= 0 for name in
                           ('loaded_units', 'entry_ticks', 'native_owners'))
                    or row['module'] in seen_modules):
                raise RuntimeError('invalid dynamic native-GVM execution witness')
            seen_modules.add(row['module'])
            directory = Path(row['artifact_directory']).resolve()
            if directory.parent != Path('/tmp') or not directory.name.startswith('beam-lisp-gvm-'):
                raise RuntimeError('dynamic artifact is outside the owned private GVM directory')
            receipt_path = directory / 'build.json'
            bind(receipt_path)
            receipt = json.loads(receipt_path.read_text())
            if (receipt.get('schema') != 'bl.native.gvm-module-build'
                    or receipt.get('status') != 'compiled-not-qualified' or receipt.get('route') != 'c'
                    or receipt.get('module_linker_name') != row['module'] + '.o1'
                    or [j['name'] for j in receipt['jobs']] != ['import', 'c']
                    or any(j.get('returncode') != 0 for j in receipt['jobs'])
                    or receipt['inputs'].get(str(directory / 'module.gvm-data')) != row['data_sha256']):
                raise RuntimeError('dynamic GVM build did not compile the witnessed DATA')
            for path, expected in receipt['inputs'].items():
                bind(path, expected)
            for path, expected in receipt['artifacts'].items():
                bind(path, expected['sha256'])
            module = directory / (row['module'] + '.o1')
            if str(module) not in receipt['artifacts'] or not elf(module):
                raise RuntimeError('dynamic GVM module is not the actual retained native artifact')
            dynamic.append({'module': row['module'], 'directory': str(directory),
                            'build_sha256': sha(receipt_path), 'native_sha256': sha(module),
                            'data_sha256': row['data_sha256']})
        if (len(rows) < 2 or rows[-1].get('retained_closures', 0) < 1
                or rows[-1].get('gc_retention_checked') is not True
                or rows[-1].get('retained_across_modules') is not True):
            raise RuntimeError('GVM Source lacks real multiunit native closure retention/GC evidence')
    except (OSError, KeyError, ValueError, RuntimeError) as error:
        witness_error = str(error)
    unchanged = all(Path(path).is_file() and sha(path) == expected for path, expected in inputs.items())
    passed = (not timed and process.returncode == 0 and witness_error is None and unchanged
              and not cleanup['errors'] and output.splitlines().count('NATIVE_COMPILER_SOURCE_CORPUS_OK') == 1)
    report = {'schema': 'bl.native.gvm-source-observation', 'version': 1,
        'runtime-abi': 1, 'backend': 'gvm', 'status': 'pass' if passed else 'failed',
        'scope': 'one actual original Source gate; full actor/self/fixpoint remains open',
        'deadline_seconds': 120, 'timeout': timed, 'exit': process.returncode,
        'seconds': round(time.monotonic() - start, 3), 'argv': argv, 'inputs': inputs,
        'inputs_unchanged': unchanged, 'cleanup': cleanup, 'route': args.route,
        'route_scope': 'selected route for startup host/compiler units; dynamic macro modules use C',
        'dynamic_route': 'c', 'source_fixture_sha256': SOURCE_FIXTURE_SHA256,
        'runtime_unit_root': env['BL_NATIVE_GVM_UNIT_ROOT'],
        'source_or_anf_interpreter': False, 'gvm_interpreter': False, 'authored_scheme_bodies': False,
        'sdk_launched': False, 'build_launched_by_checker': False,
        'dynamic_backend_builds': dynamic, 'dynamic_witnesses': len(rows),
        'last_dynamic_witness': rows[-1] if rows else None,
        'witness_valid': witness_error is None, 'witness_error': witness_error,
        'static_physical_exports': len(exports), 'static_owner_globals': len(owners),
        'log': {'path': str(log), 'sha256': sha(log)},
        'original_bundle_suffix_byte_equal': proof.read_bytes().endswith(original_bundle)}
    (out / 'observation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: report[name] for name in
          ('status', 'seconds', 'timeout', 'exit', 'dynamic_witnesses', 'witness_error')}), flush=True)
    print(output[-3000:], flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
