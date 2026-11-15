#!/usr/bin/env python3
"""One bounded exact-host helper partition pilot; original17BL objects stay fixed.

Gambit READ/WRITE extracts unique never-set bare function definitions only.
Helper units use O1; all remaining original-order FFI/initializers use O0.
No SDK/BL Source/ANF compile or original artifact changes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
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
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--baseline', type=Path, default=Path('research/native-seed/out/warm-core-baseline-v2'))
    parser.add_argument('--target-proof', type=Path, default=Path('research/native-seed/out/linked-incremental-v1/proof.json'))
    parser.add_argument('--runtime-deadline', type=int, choices=(40, 60), default=60)
    args = parser.parse_args()
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    compiler = base / 'out/compiler-native-owner'
    out, baseline = args.out.resolve(), args.baseline.resolve()
    if out.exists():
        parser.error('select a fresh helper-pilot output directory')
    inputs, original_inputs = {}, {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = sha(path)
        if expected is not None and actual != expected:
            raise RuntimeError('diagnostic input changed: ' + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError('input changed during preparation: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def data(path, limit=32 * 1024 * 1024):
        path = Path(path).resolve()
        bind(path)
        if path.stat().st_size > limit:
            raise RuntimeError('diagnostic DATA exceeds its finite bound')
        return json.loads(path.read_text())

    def unchanged():
        if any(sha(path) != expected for path, expected in inputs.items()):
            raise RuntimeError('diagnostic or original input changed during observation')
        if any(sha(path) != expected for path, expected in original_inputs.items()):
            raise RuntimeError('original qualification inputs changed')

    bind(here)
    qualified_path = compiler / 'full-native-build.json'
    qualified = data(qualified_path)
    if ((qualified.get('schema'), qualified.get('version'), qualified.get('status')) !=
            ('bl.native.full-bounded-build', 1, 'qualified') or qualified['compile_deadline_seconds'] != 120):
        raise RuntimeError('requires original bounded native qualification')
    for name, expected in qualified['inputs'].items():
        path = Path(name)
        path = path if path.is_absolute() else base / path
        bind(path, expected)
        original_inputs[str(path.resolve())] = expected
    stage = next(row for row in qualified['builds'] if row['stage'] == 'stage1')
    units = stage['units']
    if (len(units) != 18 or [row['ordinal'] for row in units] != list(range(18))
            or any(row['c_flags'][0] != '-O0' for row in units)
            or stage['link_order'] != [row['c'] for row in units]
            or not units[0]['indivisible_ffi_host'] or units[0]['bytes'] != 205727):
        raise RuntimeError('requires exact18original O0 objects with indivisible ordinal-zero host')
    image, source, bundle, host = (compiler / name for name in ('stage1', 'stage1.scm', 'bundle.scm', 'host.scm'))
    bind(image, stage['executable_sha256'])
    bind(source, stage['source_sha256'])
    bind(bundle)
    bind(host, 'd00c0c75a33cc4afc90315620d3039c48ed31464fdc0c32e5ac2841aa9d1ab8a')
    bind(stage['split_manifest'], stage['split_manifest_sha256'])
    for row in units:
        bind(row['c'], row['c_sha256'])
        bind(row['object'], row['object_sha256'])
        bind(Path(row['c']).with_suffix('.scm'), row['sha256'])
    # Gambit's generated link metadata depends on exact ordered C translations,
    # independent of the optimization level of their later object compilation.
    expected_c = [{'c': row['c'], 'c_sha256': row['c_sha256']} for row in units]
    candidates = []
    for path in (compiler / 'native-link-cache').glob('*/link-c.json'):
        candidate = json.loads(path.read_text())
        if candidate.get('request', {}).get('units') == expected_c:
            candidates.append((path, candidate))
    if len(candidates) != 1:
        raise RuntimeError('requires one exact existing link-metadata selection')
    link_receipt_path, link_receipt = candidates[0]
    bind(link_receipt_path)
    link_request = link_receipt['request']
    link_c, link_o = (link_receipt_path.parent / name for name in ('program_.c', 'program_.o'))
    bind(link_c, link_receipt['outputs']['program_.c'])
    object_receipt_path = link_receipt_path.with_name('link-object.json')
    object_receipt = data(object_receipt_path)
    if object_receipt['request'] != {
            'link': link_request, 'c_sha256': sha(link_c), 'flags': stage['link_metadata_c_flags']}:
        raise RuntimeError('existing link-object recipe differs')
    bind(link_o, object_receipt['outputs']['program_.o'])
    expected_native = {
        'link': link_request, 'link_object_sha256': sha(link_o),
        'objects': [{'path': row['object'], 'sha256': row['object_sha256'], 'flags': row['c_flags']} for row in units],
        'link_flags': stage['native_link_flags']}
    executable_receipts = []
    for path in link_receipt_path.parent.glob('images/*/native-link.json'):
        candidate = json.loads(path.read_text())
        if candidate.get('request') == expected_native and candidate.get('outputs') == {'program': stage['executable_sha256']}:
            executable_receipts.append(path)
    if len(executable_receipts) != 1:
        raise RuntimeError('original executable receipt does not authenticate these exact link inputs')
    bind(executable_receipts[0])
    bind(executable_receipts[0].with_name('program'), stage['executable_sha256'])
    # Reuse the existing fixed transport's pinned actual Clang code inventory;
    # capture hashes files only. No dynamic module or GSC job starts here.
    target = data(args.target_proof)
    bind(target['tool_request'], target['tool_request_sha256'])
    request = data(target['tool_request'], 1048576)
    request['standard_bindings'] = True
    sys.path.insert(0, str(base))
    import native_module
    import native_elf
    tool_identity, config, tool_inputs, _ = native_module.capture(request, base)
    for path, expected in tool_inputs.items():
        bind(path, expected)
    if config['flags'] != units[0]['c_flags']:
        raise RuntimeError('current fixed C ABI flags differ from original ordinal-zero compilation')
    helper_flags = ['-O1', *units[0]['c_flags'][1:]]
    remainder_flags = units[0]['c_flags']
    helper_path = base / 'check-self-emission.py'
    bind(helper_path)
    spec = importlib.util.spec_from_file_location('helper_pilot_owned_tree', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    preparation = data(baseline / 'preparation.json')
    if preparation['schema'] != 'bl.native.warm-core-benchmark-preparation':
        raise RuntimeError('requires original same-Source warm-core baseline')
    for path, expected in preparation['inputs'].items():
        bind(path, expected)
    observer_path = Path(preparation['native']['observer']['path'])
    bind(observer_path, preparation['native']['observer']['sha256'])
    original_bundle = bundle.read_bytes()
    original_observer = observer_path.read_bytes()
    if not original_observer.endswith(b'\n' + original_bundle):
        raise RuntimeError('baseline observer lacks byte-identical original bundle suffix')
    prefix = original_observer[:-len(original_bundle)-1].decode()
    old_output = literal(str(baseline / 'native.scm'))
    if prefix.count(old_output) != 1:
        raise RuntimeError('baseline output attribution differs')
    prefix = prefix.replace(old_output, literal(str(out / 'native.scm')))
    expected_output = baseline / 'beam.scm'
    bind(expected_output)
    for name in ('native.log', 'beam.log'):
        bind(baseline / name)
    comparator = base / 'benchmark/compare-benchmark.py'
    bind(comparator)
    spec = importlib.util.spec_from_file_location('helper_pilot_comparator', comparator)
    comparison = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(comparison)
    control_native, control_beam = (comparison.observations(baseline / name) for name in ('native.log', 'beam.log'))
    identity = {'schema': 'bl.native.exact-host-helper-partition-pilot-identity', 'version': 1,
        'script_sha256': sha(here), 'original_qualification': {'path': str(qualified_path), 'sha256': sha(qualified_path)},
        'tools': tool_identity, 'original_source_sha256': stage['source_sha256'],
        'original_image_sha256': stage['executable_sha256'],
        'original_host_c': {'path': units[0]['c'], 'sha256': units[0]['c_sha256']},
        'helper_c_flags': helper_flags, 'remainder_c_flags': remainder_flags,
        'original_host_source': {'path': str(host), 'sha256': sha(host)},
        'canonical_host_unit': {'path': str(Path(units[0]['c']).with_suffix('.scm')), 'sha256': units[0]['sha256']},
        'link_flags': stage['native_link_flags'],
        'original_link_object_for_admission': {'path': str(link_o), 'sha256': sha(link_o)},
        'reused_tail_objects': [{'ordinal': row['ordinal'], 'path': row['object'], 'sha256': row['object_sha256']}
                                for row in units[1:]]}
    out.mkdir(parents=True)
    report = {'schema': 'bl.native.exact-host-helper-partition-pilot', 'version': 1,
        'status': 'building', 'qualification': False, 'executed': False,
        'identity': identity, 'inputs': inputs, 'original_frozen_input_count': len(original_inputs),
        'jobs': [], 'compile_deadline_seconds': 120, 'runtime_deadline_seconds': args.runtime_deadline,
        'sdk_started': False, 'bl_source_or_anf_compiler_started': False,
        'scheme_compiler_started': False, 'original_tail_objects_reused': 17,
        'existing_link_metadata_reused': False, 'scheme_unit_target_bytes': 16384,
        'source_forms_executed_by_partitioner': False, 'host_units': []}

    def save():
        native_module.save_json(out / 'observation.json', report)

    def run(name, argv, cwd=None, build=False):
        # Same process callback/owner pattern as native_module.main.
        log = out / (name + '.log')
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
            raise RuntimeError('helper-pilot child failed: ' + name)
        return log

    try:
        scheme_dir = out / 'host-scheme'
        scheme_dir.mkdir()
        partitioner = here.with_name('partition-host.scm')
        bind(partitioner)
        partition_driver = out / 'partition-driver.scm'
        partition_driver.write_text(
            '(define pilot-input ' + literal(str(Path(units[0]['c']).with_suffix('.scm'))) + ')\n'
            + '(define pilot-frozen-input ' + literal(str(host)) + ')\n'
            + '(define pilot-output ' + literal(str(scheme_dir)) + ')\n'
            + '(define pilot-target 16384)\n(define pilot-hard 1048576)\n'
            + partitioner.read_text())
        log = run('host-read-write-partition', [config['gsi'], partition_driver])
        text = log.read_text()
        if text.count('PARTITION_ACCEPTED') != 1:
            raise RuntimeError('Gambit classifier did not admit the exact host partition')
        selected, delayed, plan = [], [], None
        for line in text.splitlines():
            fields = line.split('\t')
            if fields[0] == 'UNIT' and len(fields) == 5:
                role, name, count, size = fields[1:]
                path = scheme_dir / name
                if (role not in ('O0', 'O1') or Path(name).name != name
                        or path.stat().st_size != int(size) or not 0 < int(size) <= 1048576
                        or (role == 'O1' and int(size) > 16384)):
                    raise RuntimeError('invalid bounded partition row')
                selected.append({'path': str(path), 'sha256': bind(path), 'role': role,
                                 'forms': int(count), 'bytes': int(size)})
            elif fields[0] == 'PLAN' and len(fields) == 6:
                if plan is not None:
                    raise RuntimeError('duplicate partition plan')
                plan = dict(zip(('original_forms', 'eligible_helpers', 'remainder_forms',
                                 'helper_units', 'eager_reflection_risks'), map(int, fields[1:])))
            elif fields[0] == 'DELAYED_REFLECTION' and len(fields) == 2:
                delayed.append(fields[1])
            elif line != 'PARTITION_ACCEPTED':
                raise RuntimeError('unexpected partitioner output: ' + line)
        if (plan is None or not selected or selected[-1]['role'] != 'O0'
                or any(row['role'] != 'O1' for row in selected[:-1])
                or plan['eager_reflection_risks'] != 0
                or plan['helper_units'] != len(selected)-1
                or plan['eligible_helpers'] != sum(row['forms'] for row in selected[:-1])
                or plan['remainder_forms'] != selected[-1]['forms']
                or plan['original_forms'] != plan['eligible_helpers']+plan['remainder_forms']):
            raise RuntimeError('incomplete partition/reconstruction facts')
        identity['partition'] = selected
        identity['partitioner'] = {'path': str(partitioner), 'sha256': sha(partitioner)}
        report['partition'] = {**plan, 'units': selected, 'delayed_reflection_helpers': delayed,
                               'max_helper_bytes': max(row['bytes'] for row in selected[:-1]),
                               'remainder_bytes': selected[-1]['bytes'],
                               'roundtrip_and_original_order_reconstruction': True,
                               'fixed_host_sha256': sha(host),
                               'canonical_host_unit_sha256': units[0]['sha256'],
                               'qualified_and_frozen_host_forms_equal': True}
        unchanged()
        save()
        print(json.dumps({'partition': report['partition']}), flush=True)
        if args.plan_only:
            report['status'] = 'planned-not-compiled'
            save()
            return
        c_units, host_objects = [], []
        report['scheme_compiler_started'] = True
        for ordinal, row in enumerate(selected):
            scheme = Path(row['path'])
            cfile = out / ('host-unit-' + str(ordinal) + '.c')
            obj = out / ('host-unit-' + str(ordinal) + '.' + row['role'] + '.o')
            flags = helper_flags if row['role'] == 'O1' else remainder_flags
            run('host-unit-' + str(ordinal) + '-scheme-to-c',
                [config['gsc'], '-c', *stage['scheme_compiler_flags'], '-o', cfile, scheme],
                cwd=out, build=True)
            run('host-unit-' + str(ordinal) + '-c-' + row['role'],
                [config['clang'], *flags, '-c', cfile, '-o', obj], cwd=out, build=True)
            report['host_units'].append({'ordinal': ordinal, 'source': row,
                'c': {'path': str(cfile), 'sha256': sha(cfile)},
                'object': {'path': str(obj), 'sha256': sha(obj)}, 'c_flags': flags,
                'scheme_compiler_flags': stage['scheme_compiler_flags']})
            c_units.append(cfile)
            host_objects.append(obj)
            save()
        c_units.extend(Path(row['c']) for row in units[1:])
        objects = host_objects + [Path(row['object']) for row in units[1:]]
        new_link_c, new_link_o = out / 'program_.c', out / 'program_.o'
        run('helper-pilot-link-metadata', [config['gsc'], '-link', '-o', new_link_c, *c_units], cwd=out, build=True)
        run('helper-pilot-link-object', [config['clang'], *stage['link_metadata_c_flags'],
                                       '-c', new_link_c, '-o', new_link_o], cwd=out, build=True)
        derived_image = out / 'stage1-helper-pilot'
        report['object_order'] = [{'path': str(path), 'sha256': sha(path)} for path in objects]
        report['C_order'] = [{'path': str(path), 'sha256': sha(path)} for path in c_units]
        report['link_metadata'] = {'path': str(new_link_c), 'sha256': sha(new_link_c)}
        report['link_object'] = {'path': str(new_link_o), 'sha256': sha(new_link_o)}
        run('helper-pilot-native-link', [config['clang'], *objects, new_link_o,
                                      *stage['native_link_flags'], '-o', derived_image], cwd=out, build=True)
        with derived_image.open('rb') as stream:
            if stream.read(4) != b'\x7fELF' or not os.access(derived_image, os.X_OK):
                raise RuntimeError('helper-pilot image is not an executable native ELF')
        report['image'] = {'path': str(derived_image), 'sha256': sha(derived_image)}
        unchanged()
        observer = out / 'observer-bundle.scm'
        observer_prefix = prefix.encode()
        observer.write_bytes(observer_prefix + b'\n' + original_bundle)
        report['observer'] = {'path': str(observer), 'sha256': sha(observer),
            'original_bundle_suffix_byte_equal': observer.read_bytes()[len(observer_prefix)+1:] == original_bundle}
        report['status'] = 'running'
        save()
        log = run('native-host-helper-benchmark', [derived_image, '--eval', observer, bundle])
        (out / 'native.log').write_bytes(log.read_bytes())
        if (out / 'native.scm').read_bytes() != expected_output.read_bytes():
            raise RuntimeError('partitioned host changed actual compiler/emitter output bytes')
        samples = comparison.observations(out / 'native.log')
        report['phases'] = {}
        for phase, observations in samples.items():
            current = statistics.median(observations.values())
            old = statistics.median(control_native[phase].values())
            beam = statistics.median(control_beam[phase].values())
            report['phases'][phase] = {'seconds_per_operation': list(observations.values()),
                'median_seconds': current, 'original_native_median_seconds': old, 'beam_median_seconds': beam,
                'original_native_over_helper_pilot_ratio': old/current, 'helper_pilot_over_beam_ratio': current/beam}
        unchanged()
        report.update(status='observed-not-qualified', executed=True, scheme_byte_equal=True,
                      original_frozen_inputs_unchanged=True, protocol=preparation['protocol'])
        save()
        print(json.dumps({phase: {'original_native_over_helper_pilot': row['original_native_over_helper_pilot_ratio'],
                                 'helper_pilot_over_beam': row['helper_pilot_over_beam_ratio']}
                          for phase, row in report['phases'].items()}), flush=True)
    except BaseException as error:
        report.update(status='failed', error=str(error))
        save()
        raise


if __name__ == '__main__':
    main()
