#!/usr/bin/env python3
"""Qualify three actual dynamic C units in one already compiled host process.

Root runs this under its sequential memory/deadline wrapper. This script does
not invoke BL or rebuild a host. The native host itself compiles each dynamic
unit under its existing 120-second bounded loader policy.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=Path, required=True, help='already compiled exact direct host.o1')
    parser.add_argument('--manifest', type=Path, default=base / 'out/direct-loader-corpus/manifest.json')
    parser.add_argument('--evidence', type=Path, default=base / 'evidence/direct-loader')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    report_path = args.evidence / 'qualification.json'
    report_path.unlink(missing_ok=True)
    report = {'schema': 'bl.native.direct-loader-qualification', 'version': 1, 'status': 'running',
              'full_compiler_fixpoint': False, 'actor_corpus': False, 'independent_runtime': False}
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        value = sha(path)
        if expected is not None and value != expected:
            raise RuntimeError('dynamic corpus identity mismatch: ' + str(path))
        inputs[str(path)] = value
        return path

    try:
        host = bind(args.host)
        bind(here)
        bind(args.manifest)
        tools_path = bind(base / 'toolchain-pin.json')
        tools = json.loads(tools_path.read_text())
        gsi = bind(Path(tools['gambit']) / 'bin/gsi')
        manifest = json.loads(args.manifest.read_text())
        if manifest.get('schema') != 'bl.native.direct-loader-corpus' or manifest.get('version') != 1 or len(manifest['units']) != 3:
            raise RuntimeError('expected three exact original-source dynamic units')
        fixture = manifest['fixture']
        bind(root / fixture['path'], fixture['sha256'])
        for row in manifest['inputs']:
            bind(root / row['path'], row['sha256'])
        units = [bind(Path(row['path']) if Path(row['path']).is_absolute() else root / row['path'], row['sha256']) for row in manifest['units']]
        driver = args.evidence / 'driver.scm'
        q = lambda value: json.dumps(str(value), ensure_ascii=False)
        driver.write_text('(load ' + q(host) + ')\n'
            '(define (loader-check ok label) (if (not ok) (error "dynamic C retention failed" label)))\n'
            '(define one (native-c-eval-unit (native-eval-string (native-read-file ' + q(units[0]) + '))))\n'
            '(define two (native-c-eval-unit (native-eval-string (native-read-file ' + q(units[1]) + '))))\n'
            '(loader-check (and (native-c-closure? one) (native-c-closure? two)) "actual C functions")\n'
            '(##gc)\n'
            '(loader-check (= 17 (bl-invoke one (list 7))) "first after second load")\n'
            '(loader-check (= 14 (bl-invoke two (list 7))) "second independent control")\n'
            '(native-register! "native.loader" "first-function" one)\n'
            '(native-intern "native.loader" "first-function" one)\n'
            '(define three (native-c-eval-unit (native-eval-string (native-read-file ' + q(units[2]) + '))))\n'
            '(loader-check (native-c-closure? three) "third actual C function")\n'
            '(native-register! "native.loader" "first-function" (lambda (x) -999))\n'
            '(native-intern "native.loader" "first-function" (lambda (x) -999))\n'
            '(set! one #f) (##gc)\n'
            '(loader-check (= 18 (bl-invoke three (list 8))) "third retains first after rebinding and GC")\n'
            '(loader-check (= 16 (bl-invoke two (list 8))) "second survives third load")\n'
            '(loader-check (= 3 (length native-c-loaded-artifacts)) "three actual native loads")\n'
            '(display "DIRECT_LOADER_RETAINED 3; first-after-second; third-captures-first; GC\\n")\n')
        bind(driver)
        report['inputs'] = inputs
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        started = time.monotonic()
        # Three existing loader deadlines, plus bounded execution/cleanup.
        process = subprocess.Popen([str(gsi), str(driver.resolve())], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True)
        try:
            output, _ = process.communicate(timeout=390)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            (args.evidence / 'run.log').write_text(output)
            raise
        log = args.evidence / 'run.log'
        log.write_text(output)
        expected = 'DIRECT_LOADER_RETAINED 3; first-after-second; third-captures-first; GC'
        if process.returncode or output.splitlines() != [expected]:
            raise RuntimeError('dynamic loader witness failed: ' + output[-3000:])
        if any(sha(path) != value for path, value in inputs.items()):
            raise RuntimeError('dynamic loader input changed')
        report.update({'status': 'pass', 'seconds': round(time.monotonic() - started, 3),
                       'actual_units_retained': 3, 'cross_unit_capture': True, 'gc_after_loads': True,
                       'log': {'path': str(log.resolve()), 'sha256': sha(log)}})
        print(expected)
    except BaseException as error:
        report.update({'status': 'fail', 'error': str(error)})
        raise
    finally:
        report['inputs_after'] = {path: sha(path) if Path(path).is_file() else None for path in inputs}
        report_path.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
