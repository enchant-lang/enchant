#!/usr/bin/env python3
"""Run unchanged original actors against existing bounded C compiler stages.

Reuses a complete retained JS oracle and exact compiled objects. Starts no BL,
compiler child, Source parser or JavaScript rebuild. Full actor qualification
requires stage2 and stage3, each at default/17/41, within 120 seconds per run.
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
from artifacts import BUDGETS, ORIGINAL, ZERO, CLOCK_MODEL, Witness, actor_plan, compiler_stage, observe, sha


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actors', type=Path, required=True)
    parser.add_argument('--stage', action='append', required=True, help='stage2=/absolute/plan (then stage3=...)')
    parser.add_argument('--oracle', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, default=base / 'evidence/direct-original-actors')
    parser.add_argument('--budget', choices=BUDGETS, action='append')
    parser.add_argument('--run-timeout', type=int, default=120)
    args = parser.parse_args()
    budgets = list(dict.fromkeys(args.budget or BUDGETS))
    stages = {}
    for arg in args.stage:
        name, separator, path = arg.partition('=')
        if not separator or name not in ('seed', 'stage1', 'stage2', 'stage3') or name in stages:
            parser.error('each --stage must be a distinct seed|stage1|stage2|stage3=plan')
        stages[name] = Path(path).resolve()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / 'qualification.json'
    report_path.unlink(missing_ok=True)
    report = {'schema': 'bl.native.direct-original-actor-qualification', 'version': 1,
              'status': 'running', 'builds_launched': False, 'source_parser': False,
              'original_actor_corpus_qualified': False, 'compiler_fixpoint': False,
              'independent_runtime': False, 'same_core_overlay': False,
              'runs': [], 'results': {}, 'stages': list(stages), 'budgets': budgets}
    witness = Witness(root)
    logs = {}

    def save():
        report['inputs'] = witness.inputs
        report_path.write_text(json.dumps(report, indent=2) + '\n')

    def load_line(path):
        return '(load ' + json.dumps(str(path), ensure_ascii=False) + ')\n'

    def run(name, budget, program, gsi):
        log = evidence / (name + '-' + budget + '.log')
        log.unlink(missing_ok=True)
        argv = [str(gsi), str(program)]
        env = os.environ.copy()
        env['NATIVE_ACTOR_BUDGET'] = budget
        env.pop('BL_NATIVE_C_GC_INTERVAL', None)
        started = time.monotonic()
        process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        timed_out = False
        try:
            text, _ = process.communicate(timeout=args.run_timeout)
        except BaseException as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            text, _ = process.communicate()
            log.write_text(text)
            logs[str(log)] = sha(log)
            if not timed_out:
                raise
        log.write_text(text)
        logs[str(log)] = sha(log)
        report['runs'].append({'stage': name, 'budget': budget, 'argv': argv,
            'exit': process.returncode, 'seconds': round(time.monotonic() - started, 3), 'timed_out': timed_out})
        save()
        witness.unchanged()
        if timed_out or process.returncode:
            raise RuntimeError(name + '/' + budget + (' deadline' if timed_out else ' exit ' + str(process.returncode)) + ': ' + text[-3000:])
        return observe(text, budget)

    try:
        if not 1 <= args.run_timeout <= 120:
            raise RuntimeError('original actors retain their 120-second runtime deadline')
        witness.bind(here)
        witness.bind(here.with_name('artifacts.py'))
        actor = actor_plan(witness, args.actors)
        witness.bind(args.actors / 'build-evidence.json')
        build = json.loads((args.actors / 'build-evidence.json').read_text())
        if (build.get('schema') != 'bl.native.direct-original-actor-build'
                or build.get('status') != 'built-not-executed' or build.get('actor_run') is not False
                or build.get('parent_core_rebuilt') is not False):
            raise RuntimeError('bounded original actor objects have not been built')
        if [r['name'] for r in build['objects']] != ['actorhost', *[u['name'] for u in actor['units']]]:
            raise RuntimeError('compiled actor object order differs')
        for row in build['objects']:
            witness.bind(args.actors / (row['name'] + '.o1'), row['sha256'])
            witness.record(row['receipt'])
        for path, expected in build['inputs'].items():
            witness.bind(path, expected)
        tools_path = base / 'toolchain-pin.json'
        witness.bind(tools_path)
        tools = json.loads(tools_path.read_text())
        gsi = Path(tools['gambit']) / 'bin/gsi'
        witness.bind(gsi)
        witness.bind(args.oracle)
        oracle = json.loads(args.oracle.read_text())
        manifest = actor['manifest']
        if (oracle.get('schema') != 'bl.native.original-actor-oracle' or oracle.get('version') != 1
                or oracle.get('status') != 'complete' or set(oracle['budgets']) != set(BUDGETS)
                or oracle['application'] != {'path': 'research/js-actors/test.bl', 'sha256': ORIGINAL}
                or oracle['application'] != manifest['application'] or oracle['runtime'] != manifest['runtime']
                or oracle.get('clock-model') != CLOCK_MODEL
                or oracle['sdk-pin'] != manifest['sdk-pin'] or oracle['body'] != manifest['original-body']):
            raise RuntimeError('oracle and C actor capture differ in original Source/runtime/SDK/body')
        for path, expected in oracle['inputs'].items():
            witness.bind(path, expected)
        for budget in BUDGETS:
            expected = oracle['budgets'][budget]
            witness.record(expected['js_log'])
            lines = witness.path(expected['js_log']['path']).read_text().splitlines()
            labels = [line[5:] for line in lines if line.startswith('PASS ')]
            traces = [line for line in lines if line.startswith(('EXIT-PARITY ', 'SUP-PARITY ', 'SUP-TRACE '))]
            js_final = [line for line in lines if line.startswith('JS_CORPUS_WITNESS ')]
            if (expected['all_pass'] != 'js-actors: ALL PASS' or expected['all_pass'] not in lines
                    or any(line.startswith('FAIL ') for line in lines)
                    or labels != expected['labels'] or traces != expected['traces']
                    or len(labels) < 461 or len(set(labels)) != len(labels)
                    or [sum(x.startswith(p) for x in traces) for p in ('EXIT-PARITY ', 'SUP-PARITY ', 'SUP-TRACE ')] != [11, 10, 2]
                    or len(js_final) != 1 or lines[-1] != js_final[0]):
                raise RuntimeError('retained original JS oracle projection changed')
            js_witness = json.loads(js_final[0].split(' ', 1)[1])
            if js_witness.get('budget') != budget or js_witness.get('cleanup') != ZERO:
                raise RuntimeError('retained original JS oracle lacks budget/cleanup proof')
            for key in ('samples', 'deaths', 'max_procs', 'max_monitors', 'max_tables', 'max_links'):
                if not isinstance(js_witness.get(key), int) or js_witness[key] <= 0:
                    raise RuntimeError('retained original JS oracle lacks positive ' + key)
        pin = manifest['sdk-pin']
        witness.bind(Path(pin['sdk']) / 'artifact.json', pin['descriptor_sha256'])
        admitted_stages = {name: compiler_stage(witness, path, actor) for name, path in stages.items()}
        for name, parent in admitted_stages.items():
            # Both targets use this stage's actual compiled core/rt. No parent
            # command-line entry, Scheme BL definitions, second host or metadata.
            body = load_line(parent['directory'] / 'host.o1') + load_line(args.actors.resolve() / 'actorhost.o1')
            body += '(native-install-bundle! ' + (parent['directory'] / 'metadata.scm').read_text() + ')\n'
            body += '(set! native-c-backend (bl-key "c"))\n'
            order = []
            for phase in ('functions', 'initializers'):
                for origin in (parent, actor):
                    for unit in origin['units']:
                        if unit['phase'] == phase:
                            path = origin['directory'] / (unit['name'] + '.o1')
                            body += load_line(path)
                            order.append({'phase': phase, 'origin': 'stage-core' if origin is parent else 'original-actors',
                                          'path': str(path), 'sha256': sha(path)})
            body += (args.actors / 'entry.scm').read_text()
            program = evidence / (name + '-original-actors.scm')
            program.write_text(body)
            witness.bind(program)
            report['results'][name] = {'overlay_sha256': sha(program), 'load_order': order, 'budgets': {}}
            save()
            for budget in budgets:
                actual = run(name, budget, program, gsi)
                expected = oracle['budgets'][budget]
                if actual['labels'] != expected['labels'] or actual['traces'] != expected['traces']:
                    raise RuntimeError(name + '/' + budget + ' differs from original ordered JS checks/traces')
                report['results'][name]['budgets'][budget] = actual
                save()
        witness.unchanged()
        complete = list(stages) == ['stage2', 'stage3'] and budgets == list(BUDGETS)
        report.update(status='pass' if complete else 'observed-not-qualified',
                      same_core_overlay=True, original_actor_corpus_qualified=complete,
                      checks_per_budget=len(oracle['budgets']['default']['labels']))
        print(('DIRECT_ORIGINAL_ACTORS_QUALIFIED' if complete else 'DIRECT_ORIGINAL_ACTORS_OBSERVED') +
              ' ' + str(report['checks_per_budget']) + ' original checks; exact C core per stage; builds=0')
        return 0
    except BaseException as error:
        report.update(status='fail', error=str(error), original_actor_corpus_qualified=False)
        print('DIRECT_ORIGINAL_ACTORS_FAILED ' + str(error), file=sys.stderr)
        return 1
    finally:
        report['logs'] = logs
        report['inputs_after'] = {p: sha(p) if Path(p).is_file() else None for p in witness.inputs}
        save()


if __name__ == '__main__':
    raise SystemExit(main())
