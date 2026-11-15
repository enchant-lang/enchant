#!/usr/bin/env python3
"""Witness original-Source direct-C bootstrap; consume already captured plans.

No BL executable, BEAM/SDK producer, Source parser or ANF interpreter is used.
Existing bounded build-units.py owns all compilation/cache/ABI admission. Each
compiler child keeps 120 seconds; native self-emission keeps 240 seconds.
The LLVM option covers every AOT compiler/host/entry/link TU. Dynamic macros
still use the frozen host's real Clang C loader; actors use their recorded route.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

HEX = re.compile(r'[0-9a-f]{64}')
WITNESS = 'DIRECT_C_DYNAMIC_WITNESS '
REQUIRED_ROLES = ['frozen-host', 'direct-machine', 'source-control-frames', 'shared-raw-function', 'deferred-static-mfa',
                  'external-function-peeling', 'dynamic-loader', 'clang-loader', 'unit-host-services',
                  'late-compiler-router', 'pinned-compiler-configuration']


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def kill_tree(process):
    # Dynamic compiler children use their own sessions. Kill owned descendants
    # too, rather than leave their 120-second work running after a parent timeout.
    descendants, parents = {process.pid}, {}
    if Path('/proc').is_dir():
        for directory in Path('/proc').iterdir():
            if directory.name.isdigit():
                try:
                    text = (directory / 'stat').read_text()
                    parents[int(directory.name)] = int(text[text.rfind(')') + 2:].split()[1])
                except (OSError, ValueError, IndexError):
                    pass
        changed = True
        while changed:
            added = {pid for pid, parent in parents.items() if parent in descendants} - descendants
            changed = bool(added)
            descendants.update(added)
    for pid in descendants:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True, help='already captured bounded stage1 plan')
    parser.add_argument('--bundle', type=Path, required=True, help='original closed Source bundle.scm')
    parser.add_argument('--host', type=Path, required=True)
    parser.add_argument('--host-ledger', type=Path, required=True, help='owned host.components.scm DATA')
    parser.add_argument('--corpus', type=Path, default=base / 'fixtures/compiler-source.bl')
    parser.add_argument('--forwarding-corpus', type=Path, default=base / 'direct/fixtures/core-forwarding.bl')
    parser.add_argument('--actors', type=Path, required=True, help='already built full original C actor plan')
    parser.add_argument('--oracle', type=Path, required=True, help='complete retained freshly rebuilt JS oracle')
    parser.add_argument('--actor-qualifier', type=Path, default=base / 'direct/actor/qualify.py')
    parser.add_argument('--builder', type=Path, default=base / 'direct/build-units.py')
    parser.add_argument('--out', type=Path, default=base / 'out/direct-fixpoint')
    parser.add_argument('--cache', type=Path, default=base / 'out/direct-unit-cache')
    parser.add_argument('--route', choices=('c', 'llvm', 'both'), default='both')
    parser.add_argument('--standard-bindings', action='store_true')
    parser.add_argument('--host-optimization', type=int, choices=(0, 1), default=0,
                        help='optional host-only Clang optimization; no performance qualification implied')
    parser.add_argument('--unit-optimization', type=int, choices=(0, 1), default=0,
                        help='optional authored C-unit optimization; assembly/metadata/entry stay O0')
    parser.add_argument('--host-granularity', choices=('single', 'multiple'), default='single',
                        help='optional host-only public C grouping; authored units and entry retain stock grouping')
    parser.add_argument('--self-timeout', type=int, default=240)
    parser.add_argument('--run-timeout', type=int, default=120)
    parser.add_argument('--compile-timeout', type=int, default=120)
    args = parser.parse_args()
    for field in ('seed', 'bundle', 'host', 'host_ledger', 'corpus', 'forwarding_corpus', 'actors',
                  'oracle', 'actor_qualifier', 'builder', 'out', 'cache'):
        setattr(args, field, getattr(args, field).resolve())
    if not 1 <= args.self_timeout <= 240 or not all(1 <= n <= 120 for n in (args.run_timeout, args.compile_timeout)):
        raise RuntimeError('direct bootstrap retains 240-second self-emission and 120-second child/runtime ceilings')
    routes = ['c', 'llvm'] if args.route == 'both' else [args.route]
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / 'qualification.json'
    report_path.unlink(missing_ok=True)
    inputs, runs, plans, results = {}, [], {}, {}
    report = {'schema': 'bl.native.direct-bootstrap-fixpoint', 'version': 1, 'action-abi': 2, 'status': 'running',
              'source_parser': False, 'anf_interpreter': False, 'beam_launched': False,
              'sdk_producer_launched': False, 'routes': routes, 'runs': runs, 'plans': plans, 'results': results,
              'independent_runtime': False, 'dynamic_macro_route': 'pinned native Clang C loader',
              'all_runtime_llvm': False, 'compiler_fixpoint': False,
              'c_llvm_compiler_image_parity': False,
              'deadlines': {'native_self_emission': args.self_timeout, 'native_corpus': args.run_timeout,
                            'compiler_child': args.compile_timeout},
              'host_optimization': args.host_optimization, 'host_granularity': args.host_granularity,
              'unit_optimization': args.unit_optimization,
              'unit_optimization_scope': 'indexed-authored-units; assembly/metadata/entry remain O0',
              'host_variant_performance_qualified': False}

    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = sha(path)
        if expected is not None and actual != expected:
            raise RuntimeError('input identity differs: ' + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError('input changed during admission: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def record(row):
        return bind(row['path'], row['sha256'])

    def unchanged():
        for path, expected in inputs.items():
            if not Path(path).is_file() or sha(path) != expected:
                raise RuntimeError('direct bootstrap input changed: ' + path)

    def save():
        report['inputs'] = inputs
        write_json(report_path, report)

    def run(label, argv, *, env=None, timeout=None):
        argv = [str(value) for value in argv]
        started = time.monotonic()
        log = out / (label + '.log')
        process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        timed_out = False
        try:
            text, _ = process.communicate(timeout=timeout)
        except BaseException as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            kill_tree(process)
            text, _ = process.communicate()
            log.write_text(text)
            runs.append({'label': label, 'argv': argv, 'exit': process.returncode,
                'seconds': round(time.monotonic() - started, 3), 'timed_out': timed_out,
                'log': {'path': str(log), 'sha256': sha(log)}})
            save()
            raise
        log.write_text(text)
        runs.append({'label': label, 'argv': argv, 'exit': process.returncode,
            'seconds': round(time.monotonic() - started, 3), 'timed_out': timed_out,
            'log': {'path': str(log), 'sha256': sha(log)}})
        save()
        unchanged()
        if process.returncode:
            raise RuntimeError(label + ': exit ' + str(process.returncode) + '\n' + text[-5000:])
        print(label, 'PASS', flush=True)
        return text

    def admit_plan(directory):
        directory = Path(directory).resolve()
        index = directory / 'index.tsv'
        bind(index)
        lines = index.read_text(encoding='ascii').splitlines()
        if len(lines) < 2 or lines[0] != 'BL_NATIVE_DIRECT_UNITS\t1\t32' or lines[1] != 'B\t2':
            raise RuntimeError('not the captured bounded compiler index')
        files, singles, units, sources = {'index.tsv': sha(index)}, {}, [], []
        phase = 'functions'
        for line in lines[2:]:
            row = line.split('\t')
            kind = row[0]
            if kind in ('H', 'M', 'E', 'A', 'P'):
                name = {'H': 'host.scm', 'M': 'metadata.scm', 'E': 'entry.scm',
                        'A': 'assembly.scm', 'P': 'plan.manifest.scm'}[kind]
                if (len(row) != (4 if kind == 'H' else 3) or kind in singles or row[1] != name
                        or not all(HEX.fullmatch(x) for x in row[2:])):
                    raise RuntimeError('invalid singleton/host ledger digest')
                files[name] = bind(directory / name, row[2])
                singles[kind] = row
            elif kind == 'S':
                if len(row) != 4 or row[1] != str(len(sources)) or not all(HEX.fullmatch(x) for x in row[2:]):
                    raise RuntimeError('original Source order/hash row differs')
                sources.append(row)
            elif kind == 'U':
                if len(row) != 9:
                    raise RuntimeError('invalid bounded unit row length')
                _, next_phase, name, cfile, csha, scmfile, scmsha, count, recordsha = row
                if (next_phase not in ('functions', 'initializers')
                        or (phase == 'initializers' and next_phase != phase)
                        or name != 'u' + str(len(units)).zfill(4) or cfile != name + '.c' or scmfile != name + '.scm'
                        or not count.isdigit() or not 1 <= int(count) <= 32
                        or not all(HEX.fullmatch(x) for x in (csha, scmsha, recordsha))):
                    raise RuntimeError('bounded unit identity/order/count differs')
                phase = next_phase
                files[cfile] = bind(directory / cfile, csha)
                files[scmfile] = bind(directory / scmfile, scmsha)
                units.append({'name': name, 'phase': phase, 'count': int(count), 'definitions': []})
            elif kind == 'D':
                if (len(row) != 5 or not units or row[1] != units[-1]['name']
                        or row[2] != str(len(units[-1]['definitions']))
                        or not all(HEX.fullmatch(x) for x in row[3:])):
                    raise RuntimeError('original definition body/binding order differs')
                units[-1]['definitions'].append(row[3:])
            else:
                raise RuntimeError('unknown direct index row')
        if (set(singles) != {'H', 'M', 'E', 'A', 'P'} or not units or not sources
                or units[0]['phase'] != 'functions' or lines[-1].split('\t')[0] != 'P'
                or any(len(u['definitions']) != u['count'] for u in units)):
            raise RuntimeError('incomplete semantic compiler plan')
        stale = {p.name for p in directory.iterdir() if re.fullmatch(r'u[0-9]+\.(c|scm)', p.name)} - set(files)
        if stale:
            raise RuntimeError('unindexed stale semantic unit files: ' + ', '.join(sorted(stale)))
        if files['host.scm'] != inputs[str(args.host)]:
            raise RuntimeError('compiler stage has a different frozen direct host')
        if (directory / 'entry.scm').read_bytes() != b'(native-main (native-command-line))\n':
            raise RuntimeError('direct native entry differs')
        return {'directory': str(directory), 'semantic_files': files, 'sources': sources, 'units': units,
                'semantic_identity': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}

    def copy_seed(destination, seed):
        if destination.exists():
            # Never replace an existing differing plan to make a new proof.
            for name, expected in seed['semantic_files'].items():
                if not (destination / name).is_file() or sha(destination / name) != expected:
                    raise RuntimeError('existing stage1 plan differs; choose a fresh --out')
            return
        destination.mkdir(parents=True, exist_ok=True)
        for name in seed['semantic_files']:
            shutil.copy2(args.seed / name, destination / name)

    def build(directory, route, label):
        command = [sys.executable, args.builder, directory, '--build', '--cache', args.cache,
                   '--compile-timeout', str(args.compile_timeout), '--route', route,
                   '--host-optimization', str(args.host_optimization), '--host-granularity', args.host_granularity,
                   '--unit-optimization', str(args.unit_optimization)]
        if args.standard_bindings:
            command.append('--standard-bindings')
        # The builder enforces 120 seconds separately on EVERY sequential child;
        # a full bounded plan is not incorrectly treated as one 120-second job.
        run(label, command)
        receipt_path = directory / 'build-evidence.json'
        bind(receipt_path)
        receipt = json.loads(receipt_path.read_text())
        plan = admit_plan(directory)
        if (receipt.get('schema') != 'bl.native.direct-unit-build' or receipt.get('status') != 'built-not-executed'
                or receipt.get('action-abi') != 2 or receipt.get('header-action-abi') != 2
                or receipt.get('compiler_run') is not False or receipt.get('route') != route
                or receipt.get('standard_bindings') != args.standard_bindings
                or receipt.get('host_optimization') != args.host_optimization
                or receipt.get('unit_optimization') != args.unit_optimization
                or receipt.get('host_granularity') != args.host_granularity
                or [u['name'] for u in receipt['objects']] != ['host', *[u['name'] for u in plan['units']]]):
            raise RuntimeError('not an exact built bounded direct compiler image')
        for path, expected in receipt['inputs'].items():
            bind(path, expected)
        if ([flag for flag in receipt['c_flags'] if flag.startswith('-O')] != ['-O0']
                or [flag for flag in receipt['llvm_object_flags'] if flag.startswith('-O')] != ['-O0']
                or [flag for flag in receipt.get('entry_c_flags', []) if flag.startswith('-O')] != ['-O0']):
            raise RuntimeError('assembly/metadata/entry compilation must retain stock O0')
        for item in receipt['objects']:
            expected_flags = list(receipt['c_flags'])
            expected_llvm_flags = list(receipt['llvm_object_flags'])
            if item['name'] == 'host':
                expected_flags[0] = '-O' + str(args.host_optimization)
                expected_llvm_flags[0] = '-O' + str(args.host_optimization)
                if args.host_granularity == 'multiple':
                    expected_flags = ['-D___MULTIPLE_HOSTS' if flag == '-D___SINGLE_HOST' else flag
                                      for flag in expected_flags]
            else:
                expected_flags[0] = '-O' + str(args.unit_optimization)
                expected_llvm_flags[0] = '-O' + str(args.unit_optimization)
            if (item.get('c_flags') != expected_flags or item.get('llvm_object_flags') != expected_llvm_flags
                    or item.get('gsc_flags') != receipt['scheme_compiler_flags']):
                raise RuntimeError('actual per-object host/authored compilation flags differ')
            bind(directory / (item['name'] + '.o1'), item['sha256'])
            record(item['receipt'])
            physical = json.loads(Path(item['receipt']['path']).read_text())
            request = physical.get('request', {})
            if (request.get('name') != item['name'] or request.get('route') != route
                    or request.get('builder') != sha(args.builder)
                    or request.get('flags') != expected_flags
                    or request.get('llvm_object_flags') != expected_llvm_flags
                    or request.get('gsc_flags') != receipt['scheme_compiler_flags']
                    or physical.get('c_flags') != expected_flags
                    or physical.get('llvm_object_flags') != expected_llvm_flags
                    or physical.get('gsc_flags') != receipt['scheme_compiler_flags']
                    or physical.get('sha256') != item['sha256']):
                raise RuntimeError('bound object recipe does not prove actual host/authored flags')
            for artifact in item.get('c_artifacts', []):
                record(artifact)
            artifacts = item.get('llvm_artifacts', [])
            if route == 'llvm' and len(artifacts) != 2:
                raise RuntimeError('LLVM image omitted a host/authored-unit IR/object witness')
            for artifact in artifacts:
                record(artifact)
        bind(directory / 'compiler', receipt['executable']['sha256'])
        record(receipt['executable']['receipt'])
        for artifact in receipt['executable'].get('c_artifacts', []):
            record(artifact)
        artifacts = receipt['executable'].get('llvm_artifacts', [])
        if route == 'llvm' and len(artifacts) != 4:
            raise RuntimeError('LLVM image omitted entry/link IR/object witnesses')
        for artifact in artifacts:
            record(artifact)
        plan['build'] = {'path': str(receipt_path), 'sha256': sha(receipt_path), 'route': route,
                         'objects': receipt['objects'], 'executable': receipt['executable']}
        return plan

    def observe(text):
        rows = [json.loads(line[len(WITNESS):]) for line in text.splitlines() if line.startswith(WITNESS)]
        if not rows:
            raise RuntimeError('Source pass lacks actual dynamic C execution witness')
        for i, row in enumerate(rows, 1):
            if (row.get('backend') != 'c' or row.get('evaluations') != i or row.get('required_c_exports') != 9
                    or row.get('scheme_data_only') is not True or row.get('action_abi') != 2
                    or any(not isinstance(row.get(k), int) or row[k] <= 0 for k in ('loaded_units', 'c_steps'))):
                raise RuntimeError('Source witness permits fallback or lacks actual C execution')
            directory = Path(row['artifact_directory'])
            if directory.parent != Path('/tmp') or not directory.name.startswith('beam-lisp-direct-'):
                raise RuntimeError('dynamic C witness is not a private native loader artifact')
            for name in ('unit.scm', 'native-direct.h', 'unit.c', 'unit.dynamic.c', 'unit.o1', 'compile.log'):
                bind(directory / name)
        if rows[-1].get('retained_closures', 0) <= 0 or rows[-1].get('gc_retention_checked') is not True:
            raise RuntimeError('dynamic Source closures were not retained across collection')
        visible = '\n'.join(line for line in text.splitlines() if not line.startswith(WITNESS)) + '\n'
        return {'visible_output': visible, 'dynamic': rows[-1], 'events': len(rows)}

    def native_run(stage, command, label, timeout):
        env = os.environ.copy()
        env['BL_NATIVE_C_UNIT_ROOT'] = str(stage)
        env.pop('BL_NATIVE_TRACE', None)
        env.pop('BL_NATIVE_C_GC_INTERVAL', None)
        text = run(label, [stage / 'compiler', *command], env=env, timeout=timeout)
        return observe(text)

    def source_gates(stage, label, proof_bundle):
        source = native_run(stage, ['--eval', proof_bundle, args.corpus], label + '-source-corpus', args.run_timeout)
        if 'NATIVE_COMPILER_SOURCE_CORPUS_OK' not in source['visible_output'].splitlines():
            raise RuntimeError('native direct Source compiler corpus did not complete')
        forwarding = native_run(stage, ['--eval', proof_bundle, args.forwarding_corpus],
                                label + '-core-forwarding', args.run_timeout)
        if 'NATIVE_CORE_FORWARDING_TAIL_OK' not in forwarding['visible_output'].splitlines():
            raise RuntimeError('native seeded core forwarding corpus did not complete')
        return {'source': source, 'forwarding': forwarding}

    try:
        for path in (here, here.with_name('source-proof.scm.in'), args.builder, args.bundle, args.host,
                     args.host_ledger, args.corpus, args.forwarding_corpus, args.oracle, args.actor_qualifier,
                     args.actor_qualifier.with_name('artifacts.py'), base / 'sdk-pin.json', base / 'toolchain-pin.json'):
            bind(path)
        pin = json.loads((base / 'sdk-pin.json').read_text())
        descriptor = Path(pin['sdk']) / 'artifact.json'
        bind(descriptor, pin['descriptor_sha256'])
        if json.loads(descriptor.read_text())['source'] != pin['source']:
            raise RuntimeError('qualified SDK Source identity differs')
        host_json = args.host_ledger.with_suffix('.json')
        preparation = args.host_ledger.with_name('preparation.json')
        bind(host_json)
        bind(preparation)
        ledger, prepared = json.loads(host_json.read_text()), json.loads(preparation.read_text())
        if (ledger.get('schema') != 'bl.native.direct-host' or ledger.get('version') != 1 or ledger.get('action-abi') != 2
                or ledger.get('source_sha256') != sha(args.host)
                or [r['role'] for r in ledger['components']] != REQUIRED_ROLES
                or prepared.get('action-abi') != 2 or prepared.get('header-action-abi') != 2
                or prepared.get('status') != 'assembled-not-executed' or prepared.get('host_sha256') != sha(args.host)
                or prepared.get('toolchain') != json.loads((base / 'toolchain-pin.json').read_text())):
            raise RuntimeError('frozen direct host lacks its exact component/toolchain provenance')
        for path, expected in prepared['inputs'].items():
            bind(path, expected)
        bind(base / 'direct/native-direct.h', prepared['header_sha256'])
        for path in ('build-evidence.json', 'manifest.json', 'index.tsv'):
            bind(args.actors / path)
        oracle = json.loads(args.oracle.read_text())
        if (oracle.get('schema') != 'bl.native.original-actor-oracle' or oracle.get('status') != 'complete'
                or oracle.get('sdk-pin') != pin or set(oracle.get('budgets', {})) != {'default', '17', '41'}):
            raise RuntimeError('complete original actor oracle is required; no subset fallback')
        seed = admit_plan(args.seed)
        report['seed'] = seed
        tools = json.loads((base / 'toolchain-pin.json').read_text())
        for tool in (Path(tools['gambit']) / 'bin/gsc', Path(tools['clang']) / 'bin/clang'):
            bind(tool)
        template = here.with_name('source-proof.scm.in').read_text()
        prefix = template.replace('@BUNDLE_PATH@', json.dumps(str(args.bundle))).replace(
            '@LEDGER_PATH@', json.dumps(str(args.host_ledger))).encode()
        original_bundle = args.bundle.read_bytes()
        proof_bundle = out / 'source-proof-bundle.scm'
        proof_bundle.write_bytes(prefix + b'\n' + original_bundle)
        bind(proof_bundle)
        report['source_witness_bundle'] = {'path': str(proof_bundle), 'sha256': sha(proof_bundle),
                                          'original_bundle_suffix_byte_equal': proof_bundle.read_bytes()[len(prefix)+1:] == original_bundle}
        save()
        for route in routes:
            route_out = out / route
            route_out.mkdir(parents=True, exist_ok=True)
            directories = {name: route_out / name for name in ('stage1', 'stage2', 'stage3')}
            if any(directories[name].exists() for name in ('stage2', 'stage3')):
                raise RuntimeError('native self-emission requires fresh stage2/stage3 directories; choose a fresh --out')
            copy_seed(directories['stage1'], seed)
            stage1 = build(directories['stage1'], route, route + '-build-stage1')
            plans[route] = {'stage1': stage1}
            results[route] = {'stage1': source_gates(directories['stage1'], route + '-stage1', proof_bundle)}
            emitted = native_run(directories['stage1'], ['--compile-c', proof_bundle, args.host, args.host_ledger,
                                  directories['stage2']], route + '-stage1-builds-stage2', args.self_timeout)
            if not re.search(r'^NATIVE_DIRECT_SELF_EMISSION [0-9]+ bounded units$', emitted['visible_output'], re.MULTILINE):
                raise RuntimeError('stage1 did not witness fresh original-Source direct emission')
            stage2 = admit_plan(directories['stage2'])
            if stage2['sources'] != seed['sources']:
                raise RuntimeError('native stage2 replaced/omitted original Source inputs')
            plans[route]['stage2'] = build(directories['stage2'], route, route + '-build-stage2')
            results[route]['stage2'] = source_gates(directories['stage2'], route + '-stage2', proof_bundle)
            for corpus in ('source', 'forwarding'):
                if results[route]['stage1'][corpus]['visible_output'] != results[route]['stage2'][corpus]['visible_output']:
                    raise RuntimeError('native stages differ on original Source corpus: ' + corpus)
            emitted = native_run(directories['stage2'], ['--compile-c', proof_bundle, args.host, args.host_ledger,
                                  directories['stage3']], route + '-stage2-builds-stage3', args.self_timeout)
            if not re.search(r'^NATIVE_DIRECT_SELF_EMISSION [0-9]+ bounded units$', emitted['visible_output'], re.MULTILINE):
                raise RuntimeError('stage2 did not witness fresh original-Source direct emission')
            stage3 = admit_plan(directories['stage3'])
            if stage2['semantic_files'] != stage3['semantic_files']:
                raise RuntimeError('direct native stage2/stage3 semantic file set or hash differs')
            for name in stage2['semantic_files']:
                if (directories['stage2'] / name).read_bytes() != (directories['stage3'] / name).read_bytes():
                    raise RuntimeError('direct stage2/stage3 bytes differ: ' + name)
            # This proof is recorded BEFORE stage3 is built or actor qualification.
            results[route]['fixpoint'] = {'all_semantic_files_byte_equal': True,
                'files': stage3['semantic_files'], 'source_rows_equal': stage2['sources'] == stage3['sources'],
                'compared_before_stage3_build': True, 'semantic_identity': stage3['semantic_identity']}
            save()
            plans[route]['stage3'] = build(directories['stage3'], route, route + '-build-stage3')
            actor_evidence = route_out / 'actors'
            run(route + '-stage2-stage3-original-actors', [sys.executable, args.actor_qualifier,
                '--actors', args.actors, '--stage', 'stage2=' + str(directories['stage2']),
                '--stage', 'stage3=' + str(directories['stage3']), '--oracle', args.oracle,
                '--evidence', actor_evidence, '--run-timeout', str(args.run_timeout)])
            actor_report = actor_evidence / 'qualification.json'
            bind(actor_report)
            actors = json.loads(actor_report.read_text())
            if (actors.get('status') != 'pass' or actors.get('original_actor_corpus_qualified') is not True
                    or actors.get('stages') != ['stage2', 'stage3'] or actors.get('budgets') != ['default', '17', '41']
                    or actors.get('builds_launched') is not False or actors.get('same_core_overlay') is not True
                    or actors.get('backend') != 'c' or actors.get('authored_scheme_fallback') != 'forbidden'):
                raise RuntimeError('full original actor qualification was not witnessed by actual stage2/stage3 cores')
            for path, expected in actors['inputs'].items():
                bind(path, expected)
            results[route]['original_actors'] = {'path': str(actor_report), 'sha256': sha(actor_report),
                'checks_per_budget': actors['checks_per_budget'], 'actor_unit_route': actors['actor_unit_route'],
                'compiler_image_route': route, 'authored_scheme_fallback': 'forbidden'}
            unchanged()
            save()
        if routes == ['c', 'llvm']:
            if results['c']['fixpoint']['files'] != results['llvm']['fixpoint']['files']:
                raise RuntimeError('C and LLVM compiler images emitted different original-Source semantic plans')
            for corpus in ('source', 'forwarding'):
                if results['c']['stage2'][corpus]['visible_output'] != results['llvm']['stage2'][corpus]['visible_output']:
                    raise RuntimeError('whole compiler C/LLVM Source behavior differs')
            report['c_llvm_compiler_image_parity'] = True
        unchanged()
        report.update(status='qualified' if routes == ['c', 'llvm'] else 'qualified-selected-route',
                      compiler_fixpoint=True, original_actor_corpus_qualified=True,
                      full_direct_c_and_llvm=routes == ['c', 'llvm'],
                      scope='selected compiler image routes; real dynamic C macros; original actors on each stage core')
        save()
        print(('DIRECT_BOOTSTRAP_FIXPOINT_QUALIFIED ' if routes == ['c', 'llvm'] else
               'DIRECT_BOOTSTRAP_SELECTED_ROUTE_QUALIFIED ') + ','.join(routes), flush=True)
    except BaseException as error:
        report.update(status='fail', error=str(error), compiler_fixpoint=False)
        save()
        raise


if __name__ == '__main__':
    main()
