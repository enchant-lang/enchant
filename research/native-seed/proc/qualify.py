#!/usr/bin/env python3
"""Admit/run exact native proc helper fixtures; --build only compiles their ELF.

No SDK producer or BL VM starts here. GSI only splits generated Scheme data.
Run sequentially in the integrator's existing 2 GiB cgroup; every compiler,
linker and actor child retains 120 seconds. Source owns all process policy.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_elf import configuration, build_native, digest, HARD, DEADLINE

HEADER = b';; BL native compiler. Generated from canonical BL source.\n'
BUDGETS = ('default', '17', '41')
CLOCK_MODEL = {'name': 'virtual-turn-ms-v1', 'tick-ms': 1, 'event': 'completed-host-turn',
               'idle-progress': 'existing-host-wait', 'real-time': False}
ZERO = {'procs': 0, 'monitors': 0, 'tables': 0, 'names': 0, 'table_names': 0,
        'runnable': 0, 'input_sink': None, 'critical': 0, 'errors': 0}
FIXTURES = {'proc-demand': {'sha256': 'df750900eb95bbda639d369dfb30d1cdbff347a22c8fe6977012604b3f105c53', 'labels': ['bus-subscription-barrier', 'bus-declared-demand-and-start-options', 'bus-publish-first-buffered', 'bus-no-event-without-demand', 'bus-publisher-enters-real-waiter-queue', 'bus-blocked-stays-responsive', 'bus-unrelated-down-cannot-release-waiter', 'bus-publisher-waits-for-credit', 'bus-first-credit-delivers-first-event', 'bus-credit-releases-delayed-publisher', 'bus-credit-does-not-overdeliver', 'bus-second-credit-delivers-second-event', 'bus-termination-notifies-subscriber', 'bus-normal-stop-cleans-monitor', 'flow-source-and-map-retain-bl-policy', 'flow-expansion-meters-output-credit', 'flow-expansion-keeps-surplus-buffered', 'flow-expansion-renewal-drains-surplus', 'flow-expansion-exhaustion-signals-done', 'flow-expansion-cancel-releases-stage', 'full-runtime-cleanup'], 'traces': [], 'marker': 'NATIVE_PROC_DEMAND_OK'}, 'proc-composed': {'sha256': '58e42d5f4911c2122acd49c2314f0e9c31cc470fab83d86e26f0893067acf0c7', 'labels': ['composed-subscriber-ready', 'composed-one-state-two-slices', 'composed-registry-declared-key-lookup', 'composed-registry-refuses-undeclared-key', 'composed-refused-registration-preserves-relation', 'composed-first-publish-buffers', 'composed-publisher-really-blocked', 'composed-unrelated-down-no-release', 'composed-no-premature-publisher-reply', 'composed-subscriber-death-observed', 'composed-down-releases-delayed-publisher', 'composed-one-down-cleans-both-slices', 'composed-registry-retracts-index-on-death', 'composed-server-clean-stop', 'composed-supervisor-new-incarnation', 'composed-supervisor-keeps-sibling', 'composed-supervisor-child-service-resumes', 'composed-supervisor-stops-tree', 'composed-supervisor-releases-both-children', 'composed-table-heir-notification', 'composed-table-owner-normal-down', 'composed-table-owner-is-heir', 'composed-table-preserves-rows', 'composed-table-destroy-releases-store', 'composed-table-no-stale-owner', 'full-runtime-cleanup'], 'traces': ['PROC_TRACE bus registry down release cleanup', 'PROC_TRACE supervision restart sibling service shutdown', 'PROC_TRACE table transfer owner rows destroy'], 'marker': 'NATIVE_PROC_COMPOSED_OK'}}
HELPERS = {'priv/std/proc/bus.bl': '0f661669d8e1516a3e19f77e77d0cf75dd6b8af40495a18043f5a8747e79c62a', 'priv/std/proc/flow.bl': '400f70bac9c937bd63d0e133808603fc6960e3b023c8f0e69c6011b0e97f2d12', 'priv/std/proc/reg.bl': '2c72188b1e420d1c06edf43c0287c2d966039fb9418b38c60595ab4c2e26a5f1'}


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path, help='prepared fixture directory or build-runtime .source.json companion')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--reuse-build', type=Path)
    parser.add_argument('--cache', type=Path, default=base / 'out/proc-unit-cache')
    parser.add_argument('--standard-bindings', action='store_true')
    args = parser.parse_args()
    supplied = args.plan.resolve()
    manifest_path = supplied if supplied.is_file() else supplied / 'manifest.json'
    folder = (args.out.resolve() if args.out else supplied if supplied.is_dir()
              else supplied.with_name(supplied.name + '.elf'))
    folder.mkdir(parents=True, exist_ok=True)
    receipt = folder / ('build.json' if args.build else 'qualification.json')
    receipt.unlink(missing_ok=True)
    report = {'schema': 'bl.native.proc-corpus-build' if args.build else 'bl.native.proc-corpus-qualification',
              'version': 1, 'status': 'running', 'source_parser': False, 'anf_interpreter': False,
              'builds_launched': False, 'actor_execution': False, 'deadline_seconds': DEADLINE,
              'runs': [], 'units': [], 'budgets': list(BUDGETS), 'clock': CLOCK_MODEL,
              'direct_c': False, 'compiler_fixpoint': False, 'independent_runtime': False}
    inputs = {}

    def path_for(name):
        p = Path(name)
        return p.resolve() if p.is_absolute() else (root / p).resolve()

    def bind(path, expected=None):
        path = path_for(path)
        actual = digest(path)
        if expected is not None and actual != expected:
            raise RuntimeError('proc fixture input identity differs: ' + str(path))
        if str(path) in inputs and inputs[str(path)] != actual:
            raise RuntimeError('proc fixture input changed during admission: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def identity(row):
        return bind(row['path'], row['sha256'])

    def unchanged():
        for path, expected in inputs.items():
            if not Path(path).is_file() or digest(path) != expected:
                raise RuntimeError('proc fixture input changed: ' + path)

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
            text, _ = process.communicate(timeout=DEADLINE)
        except BaseException as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            text, _ = process.communicate()
            if not timed_out:
                (folder / (label + '.log')).write_text(text)
                raise
        log = folder / (label + '.log')
        log.write_text(text)
        report['runs'].append({'label': label, 'argv': [str(x) for x in argv], 'exit': process.returncode,
            'seconds': round(time.monotonic() - started, 3), 'timed_out': timed_out,
            'log': {'path': str(log), 'sha256': digest(log)}})
        save()
        unchanged()
        if timed_out or process.returncode:
            raise RuntimeError(label + (' timed out' if timed_out else ' failed') + ': ' + text[-3000:])
        print(label + ' PASS', flush=True)
        return text

    try:
        for path in (here, manifest_path, base / 'sdk-pin.json', base / 'toolchain-pin.json'):
            bind(path)
        manifest = json.loads(manifest_path.read_text())
        application = manifest['application']
        fixture = Path(application['path']).stem
        expected = FIXTURES.get(fixture)
        if (not expected or application != {'path': 'research/native-seed/fixtures/' + fixture + '.bl',
                                             'sha256': expected['sha256']}
                or manifest.get('schema') != 'bl.native.proc-corpus' or manifest.get('version') != 1
                or manifest.get('backend') != 'gambit-native' or manifest.get('source-interpreter') is not False
                or manifest.get('clock') != 'virtual-turn-ms-v1' or manifest.get('clock-model') != CLOCK_MODEL
                or manifest.get('helper-admission') != ['proc.bus', 'proc.flow', 'proc.reg']
                or manifest.get('assertion-adaptation') != 'none' or manifest.get('source-path-adaptation') != 'none'):
            raise RuntimeError('not the exact declared Source helper corpus and clock model')
        for row in [application, manifest['runtime'], manifest['host'], manifest['prelude'], manifest['leaves'],
                    manifest['program'], manifest['body'], manifest['anf'], manifest['link-manifest'], *manifest['inputs']]:
            identity(row)
        link = manifest['link']
        if (json.loads(path_for(manifest['link-manifest']['path']).read_text()) != link
                or link.get('schema') != 'bl.native.proc-link' or link.get('version') != 1
                or link.get('runtime-definitions') != 202 or link.get('source-interpreter') is not False
                or link.get('source-frames?') is not False or link.get('helper-namespaces') != ['proc.bus', 'proc.flow', 'proc.reg']
                or link['prelude'] != manifest['prelude'] or link.get('compatibility') != []):
            raise RuntimeError('helper corpus lacks its exact full canonical Source/runtime linker decisions')
        extensions = ['research/native-seed/host/virtual-turn-clock.scm',
                      'research/native-seed/host/actor-invariants.scm', 'research/native-seed/proc/witness.scm']
        if [x['path'] for x in link['host-extensions']] != extensions:
            raise RuntimeError('undeclared proc clock/invariant/witness extension')
        for row in [link['closure-manifest'], link['links'], link['host-link'], *link['host-extensions']]:
            identity(row)
        for row in link['compile-time-providers']:
            identity(row)
        for namespace, members in [('proc.bus', ['declared-demand', 'bus-clause']),
                                   ('proc.reg', ['declared-keys', 'registry-clause'])]:
            selected = [x for x in link['compile-time-providers'] if x.get('namespace') == namespace]
            if (len(selected) != 1 or selected[0].get('members') != members
                    or selected[0].get('arity') != 2 or selected[0].get('evaluation') != 'canonical-anonymous-eval'
                    or selected[0].get('namespace-publication') is not False
                    or selected[0].get('top-level-effects') is not False):
                raise RuntimeError('proc planner was not the original pure lexical capsule: ' + namespace)
        paths = ['priv/lib/js/actor/runtime.bl', 'research/native-seed/bridges.bl', *HELPERS, application['path']]
        if [x['path'] for x in link['units']] != paths or manifest['runtime']['path'] != paths[0]:
            raise RuntimeError('helper corpus replaced/omitted a canonical Source unit')
        for row in link['units']:
            bind(row['path'], row['source-sha256'])
            if row['path'] in HELPERS and row['source-sha256'] != HELPERS[row['path']]:
                raise RuntimeError('hash-admitted helper Source changed')
        pin = json.loads((base / 'sdk-pin.json').read_text())
        if link['sdk-pin'] != pin:
            raise RuntimeError('helper capture and qualified compiler SDK differ')
        bind(Path(pin['sdk']) / 'artifact.json', pin['descriptor_sha256'])
        part_path = path_for(link['closure-manifest']['path'])
        partition = json.loads(part_path.read_text())
        for row in [partition['metadata'], *partition['units']]:
            p = Path(row['path'])
            bind(p if p.is_absolute() else part_path.parent / p, row['sha256'])
        host = path_for(manifest['host']['path']).read_bytes()
        prefix = HEADER + host + b'\n'
        prelude = path_for(manifest['prelude']['path']).read_bytes()
        program = path_for(manifest['program']['path']).read_bytes()
        body = path_for(manifest['body']['path']).read_bytes()
        if (not prelude.startswith(prefix) or len(prefix) > HARD or program != prelude + b'\n' + body
                or not program.endswith(b'\n(native-proc-finish)\n')):
            raise RuntimeError('proc program changed its exact frozen core, host or emitted suffix')
        config = configuration(base, args.standard_bindings, bind)
        image = folder / 'actors-proc'
        if args.build:
            image = build_native(folder, program, prefix, config, cache=args.cache,
                reuse_build=args.reuse_build, standard_bindings=args.standard_bindings, report=report,
                bind=bind, path_for=path_for, run=run, save=save, image_name='actors-proc')
            report.update(status='built-not-executed', manifest={'path': str(manifest_path), 'sha256': digest(manifest_path)},
                          program_sha256=digest(path_for(manifest['program']['path'])),
                          image={'path': str(image), 'sha256': digest(image)})
            print('NATIVE_PROC_CORPUS_BUILT ' + fixture + '; actor execution=0')
            return 0
        bind(folder / 'build.json')
        build = json.loads((folder / 'build.json').read_text())
        if (build.get('schema') != 'bl.native.proc-corpus-build' or build.get('status') != 'built-not-executed'
                or build.get('actor_execution') is not False or build.get('tool_identity') != config['tool_identity']
                or build.get('manifest') != {'path': str(manifest_path), 'sha256': digest(manifest_path)}
                or build.get('program_sha256') != digest(path_for(manifest['program']['path']))
                or path_for(build['image']['path']) != image):
            raise RuntimeError('proc actor ELF lacks its exact compatible build receipt')
        for path, sha in build['inputs'].items():
            bind(path, sha)
        for row in [build['image'], *build['link_artifacts']]:
            identity(row)
        for row in build['units']:
            identity(row['c'])
            identity(row['object'])
        with image.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                raise RuntimeError('proc actors must run as the actual native ELF')
        report['actor_execution'] = True
        report['results'] = {}
        for budget in BUDGETS:
            env = os.environ.copy()
            env['NATIVE_ACTOR_BUDGET'] = budget
            text = run(fixture + '-' + budget, [image], env=env)
            lines = text.splitlines()
            labels = [line[5:] for line in lines if line.startswith('PASS ')]
            traces = [line for line in lines if line.startswith('PROC_TRACE ')]
            final = [line for line in lines if line.startswith('NATIVE_PROC_WITNESS ')]
            if (labels != expected['labels'] or traces != expected['traces'] or any(line.startswith('FAIL ') for line in lines)
                    or expected['marker'] not in lines or len(final) != 1 or lines[-1] != final[0]):
                raise RuntimeError('proc fixture lost/reordered an original assertion, trace or cleanup witness')
            observation = json.loads(final[0].split(' ', 1)[1])
            if (observation.get('budget') != budget or observation.get('cleanup') != ZERO
                    or any(type(observation.get(name)) is not int or observation[name] <= 0
                           for name in ('samples', 'deaths', 'max_procs', 'max_monitors'))
                    or (fixture == 'proc-composed' and observation.get('max_tables', 0) <= 0)):
                raise RuntimeError('proc fixture lacks actual lifecycle/registry/table cleanup evidence')
            clock = observation.get('clock', {})
            if (clock.get('model') != 'virtual-turn-ms-v1' or clock.get('tick_ms') != 1
                    or any(type(clock.get(name)) is not int or clock[name] < 0
                           for name in ('completed_turns', 'yield_turns', 'turn_ms', 'elapsed_ms'))
                    or clock['completed_turns'] <= 0 or clock['yield_turns'] > clock['completed_turns']
                    or clock['turn_ms'] != clock['completed_turns'] or clock['elapsed_ms'] < clock['turn_ms']
                    or (budget != 'default' and clock['yield_turns'] <= 0)):
                raise RuntimeError('proc fixture lacks its declared completed-turn clock/budget evidence')
            report['results'][budget] = observation
            save()
        unchanged()
        report.update(status='pass', fixture=fixture, backend='gambit-native',
                      canonical_helpers=['proc.bus', 'proc.flow', 'proc.reg'], checks_per_budget=len(expected['labels']))
        print('NATIVE_PROC_CORPUS_QUALIFIED ' + fixture + ' ' + str(len(expected['labels'])) + ' checks x 3 budgets')
        return 0
    except BaseException as error:
        report.update(status='fail', error=str(error))
        print('NATIVE_PROC_CORPUS_FAILED ' + str(error), file=sys.stderr)
        return 1
    finally:
        save()


if __name__ == '__main__':
    sys.exit(main())
