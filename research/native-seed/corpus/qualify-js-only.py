#!/usr/bin/env python3
"""Qualify ONLY exact production JS original461 at all three budgets.

No SDK, compiler, graph build, native process or mutable native producer input.
The oracle retains the original body/clock identity for target comparison; this
receipt never claims a fresh native qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from js_admission import admit, observe, ORIGINAL, BUDGETS, CLOCK_MODEL


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/sdk-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--evidence', type=Path, default=base / 'evidence/original-actor-js-only')
    parser.add_argument('--node', type=Path, default=shutil.which('node'))
    args = parser.parse_args()
    folder = args.evidence.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    receipt, oracle_path = folder / 'qualification.json', folder / 'oracle.json'
    receipt.unlink(missing_ok=True)
    oracle_path.unlink(missing_ok=True)
    inputs = {}
    report = {'schema': 'bl.native.original-js-qualification', 'version': 1, 'status': 'running',
              'scope': 'original complete production-JS corpus only', 'budgets': BUDGETS,
              'builds_launched': False, 'native_execution': False, 'native_qualification': False,
              'compiler_fixpoint': False, 'runs': [], 'results': {}}

    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def path_for(name):
        p = Path(name)
        return p.resolve() if p.is_absolute() else (root / p).resolve()

    def bind(path, expected=None):
        p = path_for(path)
        actual = digest(p)
        if expected is not None and actual != expected:
            raise RuntimeError('JS oracle input changed: ' + str(p))
        if str(p) in inputs and inputs[str(p)] != actual:
            raise RuntimeError('JS oracle input changed during admission: ' + str(p))
        inputs[str(p)] = actual
        return actual

    def unchanged():
        for path, expected in inputs.items():
            if not Path(path).is_file() or digest(path) != expected:
                raise RuntimeError('JS oracle input changed during qualification: ' + path)

    def save():
        report['inputs'] = inputs
        receipt.write_text(json.dumps(report, indent=2) + '\n')

    def run(budget, argv):
        started = time.monotonic()
        process = subprocess.Popen([str(x) for x in argv], cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        timed_out = False
        try:
            output, _ = process.communicate(timeout=120)
        except BaseException as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            if not timed_out:
                raise
        log = folder / ('javascript-' + budget + '.log')
        log.write_text(output)
        report['runs'].append({'role': 'javascript', 'budget': budget, 'argv': [str(x) for x in argv],
            'exit': process.returncode, 'timed_out': timed_out,
            'seconds': round(time.monotonic() - started, 3),
            'log': {'path': str(log), 'sha256': digest(log)}})
        bind(log)
        unchanged()
        save()
        if timed_out or process.returncode:
            raise RuntimeError('original JS corpus failed at budget ' + budget + ': ' + output[-2000:])
        return output

    try:
        bind(here)
        manifest = admit(args.manifest.resolve(), bind, path_for,
            application={'path': 'research/js-actors/test.bl', 'sha256': ORIGINAL})
        pin = json.loads((base / 'sdk-pin.json').read_text())
        bind(base / 'sdk-pin.json')
        if (manifest['sdk-pin'] != pin or manifest.get('clock-model') != CLOCK_MODEL
                or manifest.get('javascript-clock') != 'node-real-millisecond'):
            raise RuntimeError('JS oracle Source SDK or comparison clock identity differs')
        body = manifest['original-body']
        bind(path_for(body['path']), body['sha256'])
        proof = json.loads(path_for(manifest['graph-qualification']['path']).read_text())
        old_body = proof['native_transport']['body']
        if (path_for(body['path']) != path_for(old_body['path']) or body['sha256'] != old_body['sha256']):
            raise RuntimeError('JS oracle changed the exact original comparison body')
        bind(path_for(manifest['preparer']['path']), manifest['preparer']['sha256'])
        if args.node is None:
            raise RuntimeError('JS-only oracle requires an actual Node binary')
        node = Path(args.node).resolve()
        bind(node)
        witness = base / 'corpus/js-witness.mjs'
        bind(witness)
        for budget in BUDGETS:
            output = run(budget, [node, witness, path_for(manifest['artifact']['path']), budget])
            report['results'][budget] = observe(output, budget)
            report['results'][budget].update(all_pass='js-actors: ALL PASS', js_log=report['runs'][-1]['log'])
            save()
        first = report['results']['default']
        for budget in BUDGETS[1:]:
            result = report['results'][budget]
            if result['labels'] != first['labels'] or result['traces'] != first['traces']:
                raise RuntimeError('original JS assertions/traces vary across budgets')
        unchanged()
        report.update(status='pass', sdk=pin, checks_per_budget=461, original_js_corpus_qualified=True)
        oracle = {'schema': 'bl.native.original-actor-oracle', 'version': 1, 'status': 'complete',
            'scope': 'production JavaScript only; no fresh native execution or qualification',
            'target': 'javascript', 'native-execution': False,
            'application': manifest['application'], 'runtime': manifest['runtime'], 'sdk-pin': pin,
            'body': body, 'clock-model': CLOCK_MODEL, 'javascript-clock': 'node-real-millisecond',
            'inputs': inputs, 'budgets': report['results'],
            'js-qualification': {'path': str(receipt), 'sha256': None}}
        save()
        oracle['js-qualification']['sha256'] = digest(receipt)
        oracle_path.write_text(json.dumps(oracle, indent=2) + '\n')
        print('ORIGINAL_JS_ONLY_QUALIFIED 461 x default/17/41; native executions=0', flush=True)
        return 0
    except BaseException as error:
        report.update(status='fail', error=str(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    raise SystemExit(main())
