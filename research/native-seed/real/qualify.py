#!/usr/bin/env python3
"""Compile/run the prepared real-clock canonical actor/worker gate sequentially.

Run in the integrator's existing 2 GiB cgroup. --build only builds a native ELF;
the default admits that receipt and runs default/17/41, 120 seconds per child.
No BL process, Source parser, ANF interpreter, GSI actor evaluation, or second
compiler SDK is launched. GSI only READ/WRITEs Scheme forms for bounded units.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_elf import configuration as elf_configuration, build_native

HEADER = b';; BL native compiler. Generated from canonical BL source.\n'
TARGET, HARD, DEADLINE = 256 * 1024, 1024 * 1024, 120
BUDGETS = ('default', '17', '41')
POSIX_LEAVES = [
    'native.host/clock-real!/0', 'native.host/library-open/1', 'native.host/library-close/1',
    'native.host/ffi-submit/3', 'native.host/ffi-ready?/1', 'native.host/ffi-fd/1',
    'native.host/ffi-result/1', 'native.host/ffi-close/1', 'native.host/wait-fd/2',
    'native.readiness/install!/0', 'native.readiness/open-library!/1', 'native.readiness/submit!/3',
    'native.readiness/watch!/2', 'native.readiness/close-job!/1', 'native.readiness/close-library!/1',
    'native.readiness/uninstall!/0', 'native.readiness/stats/0', 'native.readiness/fixture-library/0',
]
ZERO = {'procs': 0, 'monitors': 0, 'tables': 0, 'names': 0, 'table_names': 0,
        'runnable': 0, 'input_sink': None, 'critical': 0, 'errors': 0,
        'native_jobs': 0, 'native_libraries': 0, 'native_watches': 0, 'native_input': 0}
LABELS = [
    'ffi-worker-entered-real-blocking-call',
    'canonical-peer-progresses-while-worker-blocked',
    'canonical-timer-uses-real-monotonic-clock',
    'canonical-peer-normal-death-cleans-monitor',
    'worker-remains-blocked-until-source-release',
    'pending-ffi-retains-native-library',
    'source-releases-worker-through-scalar-ffi',
    'eventfd-wakes-canonical-input-sink-and-receive',
    'blocking-result-owned-until-source-close',
    'blocking-call-observed-by-real-clock',
    'readiness-entered-canonical-timed-wait',
    'readiness-entered-canonical-input-wait',
    'poll-observed-real-eventfd-wake',
    'source-released-jobs-and-libraries',
]


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--reuse-build', type=Path, help='exact completed bounded-build receipt; reuse matching core objects only')
    parser.add_argument('--cache', type=Path, default=base / 'out/real-actor-cache')
    parser.add_argument('--standard-bindings', action='store_true', help='same checked stock primitive declarations as the retained core build')
    args = parser.parse_args()
    folder = args.plan.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    receipt = folder / ('build.json' if args.build else 'qualification.json')
    receipt.unlink(missing_ok=True)
    report = {'schema': 'bl.native.real-actor-build' if args.build else 'bl.native.real-actor-qualification',
              'version': 1, 'status': 'running', 'source_parser': False, 'anf_interpreter': False,
              'builds_launched': False, 'actor_execution': False, 'deadline_seconds': DEADLINE,
              'runs': [], 'units': [], 'budgets': list(BUDGETS)}
    inputs = {}

    def path_for(name):
        p = Path(name)
        return p.resolve() if p.is_absolute() else (root / p).resolve()

    def bind(path, expected=None):
        path = path_for(path)
        actual = digest(path)
        if expected is not None and actual != expected:
            raise RuntimeError('input identity differs: ' + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError('input changed during admission: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def identity(record):
        return bind(record['path'], record['sha256'])

    def unchanged():
        for path, expected in inputs.items():
            if not Path(path).is_file() or digest(path) != expected:
                raise RuntimeError('qualification input changed: ' + path)

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
        report['runs'].append({'label': label, 'argv': [str(x) for x in argv], 'exit': process.returncode,
                              'seconds': round(time.monotonic() - started, 3), 'timed_out': timed_out,
                              'log': {'path': str(log), 'sha256': digest(log)}})
        save()
        unchanged()
        if timed_out or process.returncode:
            raise RuntimeError(label + (' timed out' if timed_out else ' failed') + ': ' + output[-3000:])
        print(label + ' PASS', flush=True)
        return output

    try:
        bind(here)
        bind(base / 'toolchain-pin.json')
        bind(base / 'sdk-pin.json')
        bind(folder / 'manifest.json')
        manifest = json.loads((folder / 'manifest.json').read_text())
        if (manifest.get('schema') != 'bl.native.real-actor-corpus' or manifest.get('version') != 1
                or manifest.get('backend') != 'gambit-native' or manifest.get('clock') != 'posix-monotonic'
                or manifest.get('worker-abi') != 'uint64_t (*)(uint64_t)'
                or manifest['link'].get('runtime-definitions') != 202
                or manifest['link'].get('helper-namespaces') != []
                or manifest['application']['path'] != 'research/native-seed/fixtures/actor-posix.bl'
                or manifest['runtime']['path'] != 'priv/lib/js/actor/runtime.bl'):
            raise RuntimeError('not a complete prepared canonical real actor unit')
        for row in [manifest['application'], manifest['runtime'], manifest['capability'],
                    manifest['leaves'], manifest['frozen-leaves'],
                    manifest['frozen-host'], manifest['frozen-prelude'], manifest['host'],
                    manifest['prelude'], manifest['program'], manifest['anf'], manifest['foreign-fixture'],
                    *manifest['host-addons'], *manifest['inputs']]:
            identity(row)
        original_keys = json.loads(path_for(manifest['frozen-leaves']['path']).read_text())['registered_leaves']
        actual_keys = json.loads(path_for(manifest['leaves']['path']).read_text())['registered_leaves']
        if (manifest.get('declared-leaves') != POSIX_LEAVES or len(set(original_keys)) != len(original_keys)
                or set(original_keys) & set(POSIX_LEAVES)
                or actual_keys != sorted(original_keys + POSIX_LEAVES)):
            raise RuntimeError('host capability admission is not the exact finite POSIX extension')
        link = manifest['link']
        for row in [link['closure-manifest'], link['prelude'], link['links'], link['host-link']]:
            identity(row)
        if link['host-extensions'] or link['prelude'] != manifest['prelude']:
            raise RuntimeError('unaccounted host extension or prelude substitution')
        pin = json.loads((base / 'sdk-pin.json').read_text())
        if link['sdk-pin'] != pin:
            raise RuntimeError('SDK pin differs from canonical actor capture')
        bind(Path(pin['sdk']) / 'artifact.json', pin['descriptor_sha256'])
        part_path = path_for(link['closure-manifest']['path'])
        partition = json.loads(part_path.read_text())
        for row in [partition['metadata'], *partition['units']]:
            p = Path(row['path'])
            bind(p if p.is_absolute() else part_path.parent / p, row['sha256'])
        frozen_host = path_for(manifest['frozen-host']['path']).read_bytes()
        frozen = path_for(manifest['frozen-prelude']['path']).read_bytes()
        old_prefix = HEADER + frozen_host + b'\n'
        host = path_for(manifest['host']['path']).read_bytes()
        program = path_for(manifest['program']['path']).read_bytes()
        expected_host = frozen_host + b'\n' + b'\n'.join(path_for(x['path']).read_bytes() for x in manifest['host-addons'])
        prefix = HEADER + host + b'\n'
        prelude = path_for(manifest['prelude']['path']).read_bytes()
        if (not frozen.startswith(old_prefix) or host != expected_host
                or prelude != prefix + frozen[len(old_prefix):] or not program.startswith(prelude + b'\n')
                or not program.endswith(b'\n(native-real-finish)\n') or len(prefix) > HARD):
            raise RuntimeError('frozen core/host boundary or actor artifact was changed')
        config = elf_configuration(base, args.standard_bindings, bind)
        tool_identity = config['tool_identity']
        clang = config['clang']
        fixture = folder / 'fixture.so'
        image = folder / 'actors-posix'
        if args.build:
            image = build_native(folder, program, prefix, config, cache=args.cache,
                reuse_build=args.reuse_build, standard_bindings=args.standard_bindings,
                report=report, bind=bind, path_for=path_for, run=run, save=save, image_name='actors-posix')
            run('foreign-fixture', [clang, '-shared', '-fPIC', '-pthread', path_for(manifest['foreign-fixture']['path']), '-o', fixture], build=True)
            with image.open('rb') as stream:
                if stream.read(4) != b'\x7fELF':
                    raise RuntimeError('actor image is not a native ELF')
            report.update(status='built-not-executed', manifest_sha256=digest(folder / 'manifest.json'),
                          program_sha256=digest(path_for(manifest['program']['path'])),
                          image={'path': str(image), 'sha256': digest(image)},
                          fixture={'path': str(fixture), 'sha256': digest(fixture)})
            print('NATIVE_REAL_ACTORS_BUILT; actor execution=0')
            return 0
        bind(folder / 'build.json')
        build = json.loads((folder / 'build.json').read_text())
        if (build.get('schema') != 'bl.native.real-actor-build' or build.get('status') != 'built-not-executed'
                or build.get('actor_execution') is not False or build.get('tool_identity') != tool_identity
                or build.get('manifest_sha256') != digest(folder / 'manifest.json')
                or build.get('program_sha256') != digest(path_for(manifest['program']['path']))
                or path_for(build['image']['path']) != image
                or path_for(build['fixture']['path']) != fixture):
            raise RuntimeError('real actor ELF lacks an exact compatible build receipt')
        for p, expected in build['inputs'].items():
            bind(p, expected)
        identity(build['image'])
        identity(build['fixture'])
        for row in build['units']:
            identity(row['c'])
            identity(row['object'])
        with image.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                raise RuntimeError('real actor entry must be the compiled native ELF')
        report['actor_execution'] = True
        report['results'] = {}
        for budget in BUDGETS:
            env = os.environ.copy()
            env['NATIVE_ACTOR_BUDGET'] = budget
            env['BL_NATIVE_FFI_FIXTURE'] = str(fixture)
            output = run('actors-' + budget, [image], env=env)
            lines = output.splitlines()
            labels = [x[5:] for x in lines if x.startswith('PASS ')]
            final = [x for x in lines if x.startswith('NATIVE_REAL_ACTOR_WITNESS ')]
            if (labels != LABELS or any(x.startswith('FAIL ') for x in lines)
                    or 'NATIVE_ACTOR_POSIX_OK' not in lines or len(final) != 1 or lines[-1] != final[0]):
                raise RuntimeError('canonical real actor assertions/witness are incomplete')
            actual = json.loads(final[0].split(' ', 1)[1])
            if (actual.get('budget') != budget or actual.get('cleanup') != ZERO
                    or actual.get('samples', 0) < 1 or actual.get('deaths', 0) < 2
                    or actual.get('queued', 0) < 3 or actual.get('timed_waits', 0) < 1
                    or actual.get('input_waits', 0) < 1 or actual.get('ready_wakes', 0) < 1):
                raise RuntimeError('canonical actor clock/readiness/cleanup observations are missing')
            report['results'][budget] = actual
            save()
        unchanged()
        report.update(status='pass', canonical_actor_progress=True, real_clock=True,
                      readiness_delivery='canonical-rt-pump-input-and-rt-send', backend='gambit-native',
                      direct_c=False, compiler_fixpoint=False, independent_runtime=False)
        print('NATIVE_REAL_ACTORS_QUALIFIED 14 checks x 3 budgets; canonical BL scheduler; native ELF')
        return 0
    except BaseException as error:
        report.update(status='fail', error=str(error))
        print('NATIVE_REAL_ACTORS_FAILED ' + str(error), file=sys.stderr)
        return 1
    finally:
        save()


if __name__ == '__main__':
    sys.exit(main())
