#!/usr/bin/env python3
"""Diagnostic: recompile three exact qualified reader chunks at C -O2 only.

Reuses native_module.build_module and check-self-emission.OwnedTree. Never
writes the original169 inputs, starts an SDK, or links another whole ELF.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def literal(value):
    return '"' + ''.join({'\\': '\\\\', '"': '\\"', '\n': '\\n', '\r': '\\r', '\t': '\\t'}.get(
        c, '\\x' + format(ord(c), 'x') + ';' if ord(c) < 32 or ord(c) == 127 else c) for c in value) + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=Path('research/native-seed/out/warm-core-baseline-v2'))
    parser.add_argument('--target-proof', type=Path, default=Path('research/native-seed/out/linked-incremental-v1/proof.json'))
    parser.add_argument('--cache', type=Path, default=Path('research/native-seed/out/reader-o2-objects'))
    parser.add_argument('--runtime-deadline', type=int, choices=(40, 60), default=60)
    args = parser.parse_args()
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    compiler = base / 'out/compiler-native-owner'
    out, baseline = args.out.resolve(), args.baseline.resolve()
    if out.exists():
        parser.error('select a fresh diagnostic output directory')
    inputs, frozen_inputs = {}, {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = sha(path)
        if expected is not None and actual != expected:
            raise RuntimeError('diagnostic input changed: ' + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError('diagnostic input changed during preparation: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def data(path, limit=32 * 1024 * 1024):
        path = Path(path).resolve()
        bind(path)
        if path.stat().st_size > limit:
            raise RuntimeError('diagnostic DATA exceeds its finite bound')
        return json.loads(path.read_text())

    bind(here)
    qualified = data(compiler / 'full-native-build.json')
    if (qualified.get('schema'), qualified.get('version'), qualified.get('status')) != (
            'bl.native.full-bounded-build', 1, 'qualified') or qualified['compile_deadline_seconds'] != 120:
        raise RuntimeError('requires the original bounded native qualification')
    for name, expected in qualified['inputs'].items():
        path = Path(name)
        path = path if path.is_absolute() else base / path
        bind(path, expected)
        frozen_inputs[str(path.resolve())] = expected
    stage = next(row for row in qualified['builds'] if row['stage'] == 'stage1')
    if len(stage['units']) != 18 or any(row['c_flags'][0] != '-O0' for row in stage['units']):
        raise RuntimeError('control must retain all18 original O0 objects')
    if stage['scheme_compiler_flags'] != ['-prelude', '(declare (standard-bindings) (extended-bindings))']:
        raise RuntimeError('control Scheme compiler ABI differs')
    source, image, bundle, host = (compiler / name for name in ('stage1.scm', 'stage1', 'bundle.scm', 'host.scm'))
    bind(source, stage['source_sha256'])
    bind(image, stage['executable_sha256'])
    bind(bundle)
    bind(host, 'd00c0c75a33cc4afc90315620d3039c48ed31464fdc0c32e5ac2841aa9d1ab8a')
    original_source, original_bundle = source.read_bytes(), bundle.read_bytes()
    exported = data(compiler / 'chunk-export.json')
    plan = data(compiler / 'chunks.json')
    if (plan['schema'], plan['version'], plan['inputs']) != ('bl.native.chunk-plan', 2, exported['emission_inputs']):
        raise RuntimeError('requires the original checked chunk plan')
    rows = [row for row in plan['chunks'] if row['namespace'] == 'reader']
    if [(row['offset'], row['count']) for row in rows] != [(0, 32), (32, 32), (64, 28)]:
        raise RuntimeError('reader chunk coverage differs')
    chunks = []
    position = -1
    for row in rows:
        functions = compiler / 'chunks' / (row['key'] + '.functions.scm')
        receipt = data(compiler / 'chunks' / (row['key'] + '.json'))
        bind(functions, receipt['functions_sha256'])
        if receipt['emission_record'] != row['emission_record'] or receipt['emission_inputs'] != plan['inputs']:
            raise RuntimeError('reader emitted chunk identity differs')
        chunk = functions.read_bytes()
        found = original_source.find(chunk)
        if not chunk or len(chunk) > 1024 * 1024 or original_source.count(chunk) != 1 or found <= position:
            raise RuntimeError('reader chunk is not an exact ordered part of qualified stage1 Source')
        position = found
        chunks.append((row, functions, chunk))
    # Preserve the one original reader value initializer. It is already live;
    # only exact original function registrations are loaded again.
    for row in rows:
        init = compiler / 'chunks' / (row['key'] + '.initializers.scm')
        receipt = data(compiler / 'chunks' / (row['key'] + '.json'))
        bind(init, receipt['initializers_sha256'])
    preparation = data(baseline / 'preparation.json')
    if preparation['schema'] != 'bl.native.warm-core-benchmark-preparation':
        raise RuntimeError('requires the original same-Source benchmark control')
    for path, expected in preparation['inputs'].items():
        bind(path, expected)
    observed = Path(preparation['native']['observer']['path'])
    bind(observed, preparation['native']['observer']['sha256'])
    observer_bytes = observed.read_bytes()
    if not observer_bytes.endswith(b'\n' + original_bundle):
        raise RuntimeError('control observer lacks the byte-identical original owned bundle')
    prefix = observer_bytes[:-len(original_bundle)-1].decode()
    old_output = literal(str(baseline / 'native.scm'))
    if prefix.count(old_output) != 1:
        raise RuntimeError('control output attribution is not exact')
    prefix = prefix.replace(old_output, literal(str(out / 'native.scm')))
    expected_output = baseline / 'beam.scm'
    bind(expected_output)
    for name in ('native.log', 'beam.log'):
        bind(baseline / name)
    comparator = base / 'benchmark/compare-benchmark.py'
    bind(comparator)
    spec = importlib.util.spec_from_file_location('reader_o2_comparator', comparator)
    comparison = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(comparison)
    control_native, control_beam = (comparison.observations(baseline / name) for name in ('native.log', 'beam.log'))
    target = data(args.target_proof)
    request_path = Path(target['tool_request'])
    bind(request_path, target['tool_request_sha256'])
    request = data(request_path, 1048576)
    request['standard_bindings'] = True
    sys.path.insert(0, str(base))
    import native_module
    import native_elf
    tools, config, tool_inputs, _ = native_module.capture(request, base)
    for path, expected in tool_inputs.items():
        bind(path, expected)
    # Explicit derivative identity: same compiler/host/body bytes; only C O2.
    # No shared transport/configuration file changes or frozen-object relabeling.
    flags = ['-O2', *config['flags'][1:]]
    diagnostic_identity = {
        'schema': 'bl.native.original-reader-c-optimization', 'version': 1,
        'script_sha256': sha(here), 'parent_module_tools': tools,
        'original_stage1_source_sha256': stage['source_sha256'],
        'original_stage1_image_sha256': stage['executable_sha256'],
        'c_flags': [*flags, '-D___DYNAMIC'], 'scheme_compiler_flags': config['scheme_flags'],
        'reader_chunks': [{'offset': row['offset'], 'key': row['key'], 'sha256': sha(path)}
                          for row, path, chunk in chunks]}
    config['flags'] = flags
    config['tool_identity'] = {**config['tool_identity'], 'flags': flags,
                               'reader_diagnostic': diagnostic_identity}
    if config['scheme_flags'] != stage['scheme_compiler_flags']:
        raise RuntimeError('diagnostic changed original Scheme compiler declarations')
    helper_path = base / 'check-self-emission.py'
    bind(helper_path)
    spec = importlib.util.spec_from_file_location('reader_o2_owned_tree', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    out.mkdir(parents=True)
    report = {'schema': 'bl.native.original-reader-o2-diagnostic', 'version': 1,
              'status': 'building', 'qualification': False, 'executed': False,
              'inputs': inputs, 'original_frozen_input_count': len(frozen_inputs),
              'identity': diagnostic_identity, 'modules': [], 'jobs': [],
              'source_or_anf_compiler_started': False, 'sdk_started': False,
              'full_elf_relinked': False, 'compile_deadline_seconds': 120,
              'runtime_deadline_seconds': args.runtime_deadline}

    def save():
        native_module.save_json(out / 'observation.json', report)

    def run(name, argv, cwd=None, build=False):
        # Same process/descendant owner used by native_module.main; no new owner.
        index = len(report['jobs'])
        log = out / ('job-' + str(index) + '-' + name + '.log')
        deadline = native_elf.DEADLINE if build else args.runtime_deadline
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(cwd), 'deadline_seconds': deadline}
        report['jobs'].append(row)
        save()
        started, timed = time.monotonic(), False
        with log.open('w') as stream:
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            tree = helper.OwnedTree(process)
            try:
                while process.poll() is None:
                    tree.discover()
                    if time.monotonic() - started >= deadline:
                        timed = True
                        break
                    time.sleep(0.05)
            finally:
                cleanup = tree.cleanup()
        row.update(exit=process.returncode, timeout=timed, seconds=time.monotonic()-started,
                   cleanup=cleanup, log={'path': str(log), 'sha256': sha(log)})
        save()
        if timed or process.returncode != 0 or cleanup['errors']:
            raise RuntimeError('reader diagnostic child failed: ' + name)
        return log

    try:
        for row, path, chunk in chunks:
            selection = native_elf.key({'identity': diagnostic_identity, 'original_chunk': row['key']})
            module = native_module.build_module(out / ('reader-' + str(row['offset'])), chunk,
                selection, config, cache=args.cache.resolve(), report=report, bind=bind, run=run, save=save)
            module['original_chunk'] = {'path': str(path), 'sha256': sha(path),
                                        'offset': row['offset'], 'count': row['count'], 'bytes': len(chunk)}
            report['modules'].append(module)
            save()
        loads = '(define reader-o2-before (native-global-exact "reader" "read-string"))\n'
        loads += ''.join('(load ' + literal(module['artifacts']['module']['path']) + ')\n'
                         for module in report['modules'])
        loads += '(if (eq? reader-o2-before (native-global-exact "reader" "read-string")) (error "original reader was not replaced"))\n'
        # Loads precede bench-reader selection; every algorithm/body remains
        # the original checked Source. Baseline prefix/protocol otherwise exact.
        observer = out / 'observer-bundle.scm'
        observer_prefix = (loads + prefix).encode()
        observer.write_bytes(observer_prefix + b'\n' + original_bundle)
        report['observer'] = {'path': str(observer), 'sha256': sha(observer),
                              'loads_precede_reader_selection': True,
                              'original_bundle_suffix_byte_equal': observer.read_bytes()[len(observer_prefix)+1:] == original_bundle}
        report['status'] = 'running'
        save()
        log = run('native-reader-o2-benchmark', [image, '--eval', observer, bundle])
        (out / 'native.log').write_bytes(log.read_bytes())
        if (out / 'native.scm').read_bytes() != expected_output.read_bytes():
            raise RuntimeError('optimized reader changed actual compiler/emitter output bytes')
        results = comparison.observations(out / 'native.log')
        report['phases'] = {}
        for phase, samples in results.items():
            value = statistics.median(samples.values())
            control = statistics.median(control_native[phase].values())
            beam = statistics.median(control_beam[phase].values())
            report['phases'][phase] = {'seconds_per_operation': list(samples.values()),
                'median_seconds': value, 'original_native_median_seconds': control,
                'beam_median_seconds': beam, 'original_native_over_reader_o2_ratio': control/value,
                'reader_o2_over_beam_ratio': value/beam}
        if any(sha(path) != expected for path, expected in inputs.items()):
            raise RuntimeError('diagnostic input changed during build/observation')
        if any(sha(path) != expected for path, expected in frozen_inputs.items()):
            raise RuntimeError('original qualification inputs changed')
        report.update(status='observed-not-qualified', executed=True,
                      scheme_byte_equal=True, original_frozen_inputs_unchanged=True,
                      protocol=preparation['protocol'])
        save()
        print(json.dumps({phase: {'original_native_over_o2': value['original_native_over_reader_o2_ratio'],
                                 'o2_over_beam': value['reader_o2_over_beam_ratio']}
                          for phase, value in report['phases'].items()}), flush=True)
    except BaseException as error:
        report.update(status='failed', error=str(error))
        save()
        raise


if __name__ == '__main__':
    main()
