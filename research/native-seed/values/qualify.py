#!/usr/bin/env python3
"""Strict current BEAM/production-JS/native values receipt; no BL process here.

Prepare once with the qualified SDK. --build compiles only the prepared native
ELF through the shared bounded/cache transport. Default verifies that build,
then executes the identical Source on native/JS against the fresh BEAM rows.
No custom arithmetic, compiler, language interpreter or numeric oracle.
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

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'research/native-seed/sdk-pin.json').is_file())
BASE = ROOT / 'research/native-seed'
sys.path.insert(0, str(BASE))
from native_elf import configuration, build_native, digest, HARD, DEADLINE

APPLICATION = {'path': 'research/native-seed/fixtures/values-parity.bl',
               'sha256': 'f073dfeee16d6078bc4c50bcdd23b7c98d1432153df56c6d9bec049f6e0e3e7a'}
CASES = ('raw-float-keys', 'raw-decimal-keys', 'persistent-map', 'persistent-vector',
         'metadata-equality', 'exact-integer', 'quotient', 'remainder', 'modulo',
         'division-float', 'decimal-add', 'decimal-scale', 'unicode', 'tail-call',
         'multi-callable', 'self-identity')
HEADER = b';; BL native compiler. Generated from canonical BL source.\n'
ACTOR_APPLICATION = {'path': 'research/js-actors/test.bl',
                     'sha256': '5f2ad8223fd9f053157b65266d3ee14e7fe8567b6196a78ed7ac955132b9a5c5'}
ORACLE_SPECS = {'lifecycle': {'family': 'lifecycle',
               'path': 'research/js-actors/verify-lifecycle.mjs',
               'binding': 'BEAM_PARITY',
               'source-sha256': '6a91affd9b08f795d272d4b4816e5bdead75a44b55ffaaa185ca52b0a206dced',
               'raw-sha256': '3af42bd8b1824e71c455dec83a91ea3bcfc3dc7f372236bc32ebf898d80658d7',
               'code-sha256': '3af42bd8b1824e71c455dec83a91ea3bcfc3dc7f372236bc32ebf898d80658d7',
               'prefixes': ['EXIT-PARITY']},
 'names': {'family': 'names',
           'path': 'research/js-actors/verify-names.mjs',
           'binding': 'BEAM_NAMES',
           'source-sha256': '7b97da69fbcfc815d9f1ae7a52954c1533dbbadd17e587ee2198b9629a2b3137',
           'raw-sha256': '57178288839edfe5947b7a6d4dd0ca80ac6b5e5e4e8db1b18156a46d128a41ed',
           'code-sha256': '57178288839edfe5947b7a6d4dd0ca80ac6b5e5e4e8db1b18156a46d128a41ed',
           'prefixes': ['NAMES-PARITY']},
 'tables': {'family': 'tables',
            'path': 'research/js-actors/verify-tables.mjs',
            'binding': 'BEAM_TABLES',
            'source-sha256': '4a3b7ba2f4afdc977e8de27f2fc440d439d4253a5aa03a267f98d218ea6fc080',
            'raw-sha256': 'f935826c83f777d48266f8862631f44d454fdd306dab57af2c9f873f2a47e69b',
            'code-sha256': 'f935826c83f777d48266f8862631f44d454fdd306dab57af2c9f873f2a47e69b',
            'prefixes': ['TABLE-PARITY']},
 'supervision': {'family': 'supervision',
                 'path': 'research/js-actors/verify-supervision.mjs',
                 'binding': 'BEAM_SUPERVISION',
                 'source-sha256': '8f6a4a70c7fc7ec2dae99f56bbe5d0f227fb8e8f9878dcffd100cba5e0126bee',
                 'raw-sha256': 'd93b6ec0f66a32d4f5d8e0d30659bca827d6d2ab3cfd38396e37056cfa51a352',
                 'code-sha256': '547c2b1cabd71deb8f62f707d0365bf5cfafa8cff5f9ec3edaec6cb03e1d0fb8',
                 'prefixes': ['SUP-PARITY', 'SUP-TRACE']}}



def check_rows(rows):
    if not isinstance(rows, list) or len(rows) != 377 or not all(isinstance(x, str) for x in rows):
        raise RuntimeError('values fixture lost an observation')
    equal, order = {}, {}
    for index, line in enumerate(rows[:361]):
        match = re.fullmatch(r'pair (\d+) (\d+) (true|false) (-1|0|1) (true|false) (true|false) (true|false) (1|2)', line)
        if not match:
            raise RuntimeError('malformed exact numeric relation: ' + line)
        i, j, eq, cmp, seq, map_value, metadata, _keys = match.groups()
        i, j, cmp = int(i), int(j), int(cmp)
        if (i, j) != divmod(index, 19) or not eq == seq == map_value == metadata or (eq == 'true') != (cmp == 0):
            raise RuntimeError('numeric equality/ordering/nested laws disagree: ' + line)
        equal[i, j], order[i, j] = eq == 'true', cmp
    for i in range(19):
        if not equal[i, i]:
            raise RuntimeError('numeric equality is not reflexive')
        for j in range(19):
            if equal[i, j] != equal[j, i] or order[i, j] != -order[j, i]:
                raise RuntimeError('numeric symmetry/antisymmetry law failed')
            for k in range(19):
                if equal[i, j] and equal[j, k] and not equal[i, k]:
                    raise RuntimeError('numeric equality is not transitive')
    if rows[361:] != ['case ' + label + ' true' for label in CASES]:
        raise RuntimeError('an existing numeric/collection/callable boundary contract failed')



def validate_actor_oracles(manifest, beam, pin, identity, path_for, report):
    """Fresh original OTP snippets against six already-qualified raw logs.

    Protocol projection is the original verifiers' rule/trace boundary. The
    original 461 assertions and recorded native/JS execution remain unchanged.
    """
    identity(manifest['actor-oracles'])
    oracle = json.loads(path_for(manifest['actor-oracles']['path']).read_text())
    if (oracle.get('schema') != 'bl.native.original-beam-actor-oracles' or oracle.get('version') != 1
            or oracle.get('status') != 'executed' or oracle.get('sdk-pin') != pin
            or oracle.get('vm-pid') != beam.get('vm-pid') or not isinstance(oracle.get('vm-pid'), str)
            or oracle.get('otp') != beam.get('otp') or oracle.get('policy-adaptation') != 'none'
            or oracle.get('optional-oracles') is not False or oracle.get('path-elixir') is not False
            or oracle.get('cancellation-scope') != ['explicit-and-linked-process-kill', 'bounded-GenServer.call-exit']
            or oracle.get('standalone-timer-cancellation-oracle') is not False):
        raise RuntimeError('fresh original BEAM actor oracles were not run in the same qualified SDK VM')
    identity(oracle['application'])
    identity(oracle['runtime'])
    if oracle['application'] != ACTOR_APPLICATION or oracle['runtime']['path'] != 'priv/lib/js/actor/runtime.bl':
        raise RuntimeError('actor observations are not from the original canonical Source')
    identity(oracle['actor-receipt'])
    receipt_path = path_for(oracle['actor-receipt']['path'])
    parent = json.loads(receipt_path.read_text())
    if (parent.get('schema') != 'bl.native.original-actor-qualification' or parent.get('version') != 1
            or parent.get('status') != 'pass' or parent.get('original_actor_corpus_qualified') is not True
            or parent.get('sdk') != pin or parent.get('checks_per_budget') != 461
            or parent.get('budgets') != ['default', '17', '41'] or parent.get('inputs') != parent.get('inputs_after')):
        raise RuntimeError('retained original actor runs lack their complete qualified immutable receipt')
    for row in (oracle['application'], oracle['runtime']):
        if parent['inputs'].get(str(path_for(row['path']))) != row['sha256']:
            raise RuntimeError('retained actor Source differs from the fresh BEAM protocol authority')
    transport = parent['native_transport']
    if (transport.get('kind') != 'compiled-native-exact-core-and-original-body'
            or transport.get('source_assertion_adaptation') != 'none' or transport.get('builds_launched') is not False):
        raise RuntimeError('retained native actor runs used a different execution/Source route')
    for field in ('build', 'source', 'body', 'image'):
        identity(transport[field])
    with path_for(transport['image']['path']).open('rb') as image:
        if image.read(4) != b'\x7fELF':
            raise RuntimeError('retained native actors are not the actual qualified ELF')
    native_build = json.loads(path_for(transport['build']['path']).read_text())
    for field in ('core', 'body', 'source', 'image'):
        if native_build[field] != transport[field]:
            raise RuntimeError('retained native build and actual actor transport differ')
    expected_counts = {'EXIT-PARITY': 11, 'NAMES-PARITY': 4, 'TABLE-PARITY': 25, 'SUP-PARITY': 10, 'SUP-TRACE': 2}

    def projection(text, prefixes):
        projected = {}
        counts = {prefix: 0 for prefix in prefixes}
        for line in text.splitlines():
            if line.startswith(('FAIL ', 'SKIP ')):
                raise RuntimeError('an actor oracle or retained run contains a failure/skip')
            for prefix in prefixes:
                if line.startswith(prefix + ' '):
                    pattern = (r'SUP-TRACE (\d+) (same|changed) (same|changed) (same|changed)'
                               if prefix == 'SUP-TRACE' else re.escape(prefix) + r' ([a-z0-9-]+) (\S+)')
                    match = re.fullmatch(pattern, line)
                    if not match:
                        raise RuntimeError('malformed original actor protocol token: ' + line)
                    key, value = prefix + ' ' + match[1], ' '.join(match.groups()[1:])
                    if key in projected:
                        raise RuntimeError('duplicate original actor protocol token: ' + key)
                    projected[key] = value
                    counts[prefix] += 1
        if counts != {prefix: expected_counts[prefix] for prefix in prefixes}:
            raise RuntimeError('missing/extra original BEAM actor protocol observations: ' + str(counts))
        return projected

    captures = oracle.get('oracles', [])
    if len(captures) != 4 or [row.get('family') for row in captures] != list(ORACLE_SPECS):
        raise RuntimeError('one original BEAM oracle was omitted/replaced/reordered')
    beam_projection = {}
    for row in captures:
        spec = ORACLE_SPECS[row['family']]
        if (row.get('binding') != spec['binding'] or row.get('status') != 'executed'
                or row.get('source') != {'path': spec['path'], 'sha256': spec['source-sha256']}
                or row.get('raw-sha256') != spec['raw-sha256'] or row.get('execution') != 'Elixir.Code.eval_string'
                or row.get('template-transport') != 'original-JS-cooked-literal' or row.get('timeout-ms') != 120000):
            raise RuntimeError('BEAM execution did not use the exact original oracle literal: ' + row['family'])
        for field in ('source', 'code', 'output'):
            identity(row[field])
        source = path_for(row['source']['path']).read_text()
        marker = 'const ' + spec['binding'] + ' = `'
        if source.count(marker) != 1:
            raise RuntimeError('ambiguous original oracle declaration')
        raw = source.split(marker, 1)[1].split('`;', 1)[0]
        # These fixed source hashes admit only untagged, uninterpolated literals
        # with the single documented default-argument backslash run.
        if '${' in raw or '`' in raw or hashlib.sha256(raw.encode()).hexdigest() != spec['raw-sha256']:
            raise RuntimeError('original oracle literal transport changed')
        cooked = raw.replace(chr(92) * 2, chr(92))
        if (hashlib.sha256(cooked.encode()).hexdigest() != spec['code-sha256']
                or row['code']['sha256'] != spec['code-sha256']
                or path_for(row['code']['path']).read_text() != cooked):
            raise RuntimeError('executed Elixir oracle differs from the original cooked JS literal')
        fields = projection(path_for(row['output']['path']).read_text(), spec['prefixes'])
        if set(fields) & set(beam_projection):
            raise RuntimeError('overlapping original oracle protocol authority')
        beam_projection.update(fields)
    logs = oracle.get('retained-actor-logs', [])
    expected_runs = {(role, budget) for role in ('native', 'javascript') for budget in ('default', '17', '41')}
    if len(logs) != 6 or {(row.get('role'), row.get('budget')) for row in logs} != expected_runs:
        raise RuntimeError('original actor comparison omitted a target/budget')
    results = {}
    for row in logs:
        role, budget = row['role'], row['budget']
        path = path_for(row['log']['path'])
        expected_path = receipt_path.parent / (role + '-' + budget + '.log')
        metadata = parent['logs'].get(str(path))
        identity(row['log'])
        if (path != expected_path or metadata != {'sha256': row['log']['sha256'], 'bytes': path.stat().st_size}):
            raise RuntimeError('retained raw actor log differs from its actual execution receipt')
        runs = [run for run in parent['runs'] if run.get('role') == role and run.get('budget') == budget]
        if len(runs) != 1 or runs[0].get('exit') != 0 or runs[0].get('timed_out') is not False:
            raise RuntimeError('actor protocol came from an incomplete/nonqualified execution')
        if role == 'native' and runs[0]['argv'] != [str(path_for(transport['image']['path']))]:
            raise RuntimeError('native protocol execution differs from its retained ELF')
        text = path.read_text()
        lines = text.splitlines()
        summary = parent['results'][budget][role]
        labels = [line[5:] for line in lines if line.startswith('PASS ')]
        traces = [line for line in lines if line.startswith(('EXIT-PARITY ', 'SUP-PARITY ', 'SUP-TRACE '))]
        witness_prefix = ('NATIVE' if role == 'native' else 'JS') + '_CORPUS_WITNESS '
        witnesses = [json.loads(line[len(witness_prefix):]) for line in lines if line.startswith(witness_prefix)]
        if (labels != summary['labels'] or len(labels) != 461 or len(set(labels)) != 461
                or traces != summary['traces'] or 'js-actors: ALL PASS' not in lines
                or witnesses != [summary['witness']] or not lines[-1].startswith(witness_prefix)):
            raise RuntimeError('retained raw output differs from its original full assertion/witness result')
        actual = projection(text, expected_counts)
        if actual != beam_projection:
            differences = sorted(key for key in set(actual) | set(beam_projection) if actual.get(key) != beam_projection.get(key))
            raise RuntimeError(role + '/' + budget + ' differs from fresh native BEAM: ' + str(differences))
        results[role + '/' + budget] = {'original_assertions': 461, 'protocol_observations': 52, 'same_as_beam': True}
    report['lifecycle_beam_parity'] = True
    report['original_actor_beam_oracles'] = {'status': 'pass', 'sdk_vm_pid': oracle['vm-pid'],
        'code': 'four exact original Elixir literals', 'fresh_beam_protocol_observations': 52,
        'counts': expected_counts, 'retained_native_js_results': results,
        'cancellation_scope': oracle['cancellation-scope'], 'standalone_timer_cancellation_oracle': False,
        'native_js_executions_launched': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path, help='prepared values directory')
    parser.add_argument('--build', action='store_true', help='compile the ELF, do not execute the fixture')
    parser.add_argument('--reuse-build', type=Path)
    parser.add_argument('--cache', type=Path, default=BASE / 'out/proc-unit-cache')
    parser.add_argument('--standard-bindings', action='store_true')
    parser.add_argument('--node', type=Path, default=shutil.which('node'))
    args = parser.parse_args()
    folder = args.plan.resolve()
    manifest_path = folder / 'manifest.json'
    receipt = folder / ('build.json' if args.build else 'qualification.json')
    receipt.unlink(missing_ok=True)
    inputs = {}
    report = {'schema': 'bl.native.values-build' if args.build else 'bl.native.values-qualification',
              'version': 1, 'status': 'running', 'scope': 'finite exact values and pure callable/collection boundaries',
              'deadline_seconds': DEADLINE, 'builds_launched': False, 'actor_execution': False,
              'numeric_oracle': 'same original BL source executed by qualified BEAM SDK',
              'source_interpreter': False, 'compiler_fixpoint': False, 'direct_c': False,
              'lifecycle_beam_parity': False, 'runs': [], 'units': []}

    def path_for(path):
        p = Path(path)
        return p.resolve() if p.is_absolute() else (ROOT / p).resolve()

    def bind(path, expected=None):
        path = path_for(path)
        actual = digest(path)
        if expected is not None and actual != expected:
            raise RuntimeError('values input identity differs: ' + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError('values input changed during admission: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def identity(row):
        return bind(row['path'], row['sha256'])

    def unchanged():
        for path, expected in inputs.items():
            if not Path(path).is_file() or digest(path) != expected:
                raise RuntimeError('values input changed: ' + path)

    def save():
        report['inputs'] = inputs
        temporary = receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(receipt)

    def run(label, argv, cwd=folder, env=None, build=False):
        report['builds_launched'] |= build
        started = time.monotonic()
        process = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True)
        timed_out = False
        try:
            output, _ = process.communicate(timeout=DEADLINE)
        except BaseException as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            if not timed_out:
                (folder / (label + '.log')).write_text(output)
                raise
        log = folder / (label + '.log')
        log.write_text(output)
        report['runs'].append({'label': label, 'argv': [str(x) for x in argv],
            'exit': process.returncode, 'timed_out': timed_out,
            'seconds': round(time.monotonic() - started, 3),
            'log': {'path': str(log), 'sha256': digest(log)}})
        save()
        unchanged()
        if timed_out or process.returncode:
            raise RuntimeError(label + (' timed out' if timed_out else ' failed') + ': ' + output[-3000:])
        return output

    try:
        for path in (Path(__file__), manifest_path, BASE / 'sdk-pin.json'):
            bind(path)
        manifest = json.loads(manifest_path.read_text())
        pin = json.loads((BASE / 'sdk-pin.json').read_text())
        if (manifest.get('schema') != 'bl.native.values-parity' or manifest.get('version') != 1
                or manifest.get('sdk-pin') != pin or manifest.get('application') != APPLICATION
                or manifest.get('observation-count') != 377 or manifest.get('source-interpreter') is not False
                or manifest.get('assertion-adaptation') != 'none' or manifest.get('source-path-adaptation') != 'none'):
            raise RuntimeError('not the exact original shared values corpus and qualified SDK')
        bind(Path(pin['sdk']) / 'artifact.json', pin['descriptor_sha256'])
        for row in [manifest['application'], manifest['beam'], *manifest['inputs']]:
            identity(row)
        beam = json.loads(path_for(manifest['beam']['path']).read_text())
        if (beam.get('schema') != 'bl.native.values-beam-oracle' or beam.get('version') != 1
                or beam.get('status') != 'executed' or beam.get('sdk-pin') != pin
                or beam.get('application') != APPLICATION or beam.get('target') != 'beam'
                or beam.get('compiler') != 'canonical-Compiler.eval_string' or beam.get('compiler-target') != 'beam'
                or beam.get('observation-count') != 377 or not isinstance(beam.get('otp'), str)):
            raise RuntimeError('missing fresh qualified-SDK BEAM execution receipt')
        check_rows(beam['rows'])
        validate_actor_oracles(manifest, beam, pin, identity, path_for, report)
        javascript, native = manifest['javascript'], manifest['native']
        for row in [javascript['parent'], javascript['qualification'], javascript['artifact'], *javascript['assets'], *native.values()]:
            identity(row)
        parent = json.loads(path_for(javascript['parent']['path']).read_text())
        if (parent.get('schema') != 'bl.native.original-actor-corpus' or parent.get('version') != 1
                or parent.get('target') != 'javascript' or parent.get('sdk-pin') != pin
                or parent.get('assertion-adaptation') != 'none' or parent.get('source-path-adaptation') != 'none'):
            raise RuntimeError('production JS graph lacks its matching Source/SDK admission')
        proof = json.loads(path_for(javascript['qualification']['path']).read_text())
        if (proof.get('schema') != 'bl.native.original-actor-qualification' or proof.get('status') != 'pass'
                or proof.get('sdk') != pin or proof.get('original_actor_corpus_qualified') is not True
                or proof.get('inputs', {}).get(str(path_for(javascript['parent']['path']))) != javascript['parent']['sha256']):
            raise RuntimeError('reused production JS graph lacks its actual prior qualification')
        for row in [*parent['inputs'], *parent['assets']]:
            identity(row)
            if proof['inputs'].get(str(path_for(row['path']))) != row['sha256']:
                raise RuntimeError('production JS input was not in its prior qualification: ' + row['path'])
        link = json.loads(path_for(native['link']['path']).read_text())
        if (link.get('schema') != 'bl.native.proc-link' or link.get('version') != 1
                or link.get('sdk-pin') != pin or link.get('runtime-definitions') != 202
                or link.get('helper-namespaces') != [] or link.get('source-frames?') is not False
                or link.get('source-interpreter') is not False or link.get('compatibility') != []
                or link.get('prelude') != native['prelude']):
            raise RuntimeError('values program lacks exact canonical runtime/compiler linkage')
        if [row['path'] for row in link['units']] != [
                'priv/lib/js/actor/runtime.bl', 'research/native-seed/bridges.bl', APPLICATION['path']]:
            raise RuntimeError('values program replaced its original Source/runtime units')
        for row in link['units']:
            bind(row['path'], row['source-sha256'])
        if [row['path'] for row in link['host-extensions']] != ['research/native-seed/values/values-witness.scm']:
            raise RuntimeError('values program added an undeclared host extension')
        for row in [link['closure-manifest'], link['links'], link['host-link'], *link['host-extensions']]:
            identity(row)
        partition_path = path_for(link['closure-manifest']['path'])
        partition = json.loads(partition_path.read_text())
        for row in [partition['metadata'], *partition['units']]:
            p = Path(row['path'])
            bind(p if p.is_absolute() else partition_path.parent / p, row['sha256'])
        host = path_for(native['host']['path']).read_bytes()
        prefix = HEADER + host + b'\n'
        prelude = path_for(native['prelude']['path']).read_bytes()
        program = path_for(native['program']['path']).read_bytes()
        if (not prelude.startswith(prefix) or len(prefix) > HARD or not program.startswith(prelude + b'\n')
                or not program.endswith(b'\n(native-values-finish)\n')):
            raise RuntimeError('values program changed its frozen compiler/host boundary')
        config = configuration(BASE, args.standard_bindings, bind)
        image = folder / 'values-native'
        if args.build:
            image = build_native(folder, program, prefix, config, cache=args.cache,
                reuse_build=args.reuse_build, standard_bindings=args.standard_bindings,
                report=report, bind=bind, path_for=path_for, run=run, save=save, image_name='values-native')
            report.update(status='built-not-executed', manifest={'path': str(manifest_path), 'sha256': digest(manifest_path)},
                program_sha256=digest(path_for(native['program']['path'])), image={'path': str(image), 'sha256': digest(image)})
            return 0
        build_path = folder / 'build.json'
        bind(build_path)
        build = json.loads(build_path.read_text())
        if (build.get('schema') != 'bl.native.values-build' or build.get('status') != 'built-not-executed'
                or build.get('actor_execution') is not False or build.get('tool_identity') != config['tool_identity']
                or build.get('manifest') != {'path': str(manifest_path), 'sha256': digest(manifest_path)}
                or build.get('program_sha256') != digest(path_for(native['program']['path']))
                or path_for(build['image']['path']) != image):
            raise RuntimeError('values ELF lacks its matching completed build receipt')
        for path, sha in build['inputs'].items():
            bind(path, sha)
        for row in [build['image'], *build['link_artifacts']]:
            identity(row)
        for row in build['units']:
            identity(row['c'])
            identity(row['object'])
        with image.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                raise RuntimeError('native values program is not an ELF')
        if args.node is None:
            raise RuntimeError('production JS comparison requires an actual Node executable')
        node = Path(args.node).resolve()
        bind(node)
        report['node_version'] = run('node-version', [node, '--version']).strip()
        report['actor_execution'] = True
        results = {}
        for target, command in [('native', [image]), ('javascript', [node, path_for(javascript['artifact']['path'])])]:
            text = run(target, command)
            lines = text.splitlines()
            rows = [line[7:] for line in lines if line.startswith('VALUES ')]
            check_rows(rows)
            if (rows != beam['rows'] or lines.count('VALUES-DONE') != 1
                    or any('FAIL ' in line or line.startswith('SKIP ') for line in lines)
                    or (target == 'native' and (lines.count('NATIVE_VALUES_CLEANUP_OK') != 1
                        or lines[-1] != 'NATIVE_VALUES_CLEANUP_OK'))):
                differences = [index for index, (actual, expected) in enumerate(zip(rows, beam['rows'])) if actual != expected]
                raise RuntimeError(target + ' differs from actual BEAM observations: ' + str(differences[:20]))
            results[target] = {'observations': len(rows), 'same_as_beam': True}
        report.update(status='pass', checks=377, results={'beam': {'observations': 377, 'executed_by': pin}, **results},
                      values_three_target_parity=True)
        unchanged()
        print('VALUES_BEAM_JS_NATIVE_PASS 377 same-source values + 52 original BEAM protocol fields at all retained budgets', flush=True)
        return 0
    except BaseException as error:
        report.update(status='fail', error=str(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    raise SystemExit(main())
