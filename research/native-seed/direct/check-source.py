#!/usr/bin/env python3
"""One actual guarded Source gate; no SDK, Source interpreter or fixpoint claim."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def main():
    base = Path(__file__).resolve().parents[1]
    root = base.parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--host-ledger', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    plan, ledger, out = args.plan.resolve(), args.host_ledger.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'observation.json').exists():
        raise RuntimeError('preserve prior observations; select a fresh output directory')
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = sha(path)
        if (expected is not None and expected != actual) or (str(path) in inputs and inputs[str(path)] != actual):
            raise RuntimeError('input changed: ' + str(path))
        inputs[str(path)] = actual
        return actual

    build_path = plan / 'build-evidence.json'
    bind(build_path)
    build = json.loads(build_path.read_text())
    if (build.get('schema') != 'bl.native.direct-unit-build' or build.get('status') != 'built-not-executed'
            or build.get('compiler_run') is not False or build.get('inputs') != build.get('inputs_after')):
        raise RuntimeError('requires an exact successful bounded compiler build')
    for path, expected in build['inputs'].items():
        bind(path, expected)
    image = plan / 'compiler'
    bind(image, build['executable']['sha256'])
    if image.read_bytes()[:4] != b'\x7fELF' or not os.access(image, os.X_OK):
        raise RuntimeError('compiler is not an executable ELF')
    tree_helper = base / 'check-self-emission.py'
    bind(tree_helper)
    spec = importlib.util.spec_from_file_location('native_owned_tree', tree_helper)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    bundle, template, corpus = plan / 'bundle.scm', base / 'direct/source-proof.scm.in', base / 'fixtures/compiler-source.bl'
    for path in (Path(__file__), bundle, ledger, template, corpus):
        bind(path)
    prefix = template.read_text().replace('@BUNDLE_PATH@', json.dumps(str(bundle))).replace(
        '@LEDGER_PATH@', json.dumps(str(ledger))).encode()
    proof = out / 'source-proof-bundle.scm'
    proof.write_bytes(prefix + b'\n' + bundle.read_bytes())
    bind(proof)
    env = os.environ.copy()
    env['BL_NATIVE_C_UNIT_ROOT'] = str(plan)
    env.pop('BL_NATIVE_TRACE', None)
    env.pop('BL_NATIVE_C_GC_INTERVAL', None)
    argv = [str(image), '--eval', str(proof), str(corpus)]
    start, timed, cleanup = time.monotonic(), False, None
    log = out / 'source.log'
    with log.open('w') as stream:
        process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        tree = helper.OwnedTree(process)
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
    rows = [json.loads(line.split(' ', 1)[1]) for line in output.splitlines()
            if line.startswith('DIRECT_C_DYNAMIC_WITNESS ')]
    witness_valid = bool(rows)
    for index, row in enumerate(rows, 1):
        witness_valid &= (row.get('backend') == 'c' and row.get('evaluations') == index
            and row.get('required_c_exports') == 9 and row.get('scheme_data_only') is True
            and all(type(row.get(name)) is int and row[name] > 0 for name in ('loaded_units', 'c_steps')))
    if rows:
        witness_valid &= rows[-1].get('retained_closures', 0) > 0 and rows[-1].get('gc_retention_checked') is True
    unchanged = all(Path(path).is_file() and sha(path) == expected for path, expected in inputs.items())
    passed = (not timed and process.returncode == 0 and witness_valid and unchanged and not cleanup['errors']
              and output.splitlines().count('NATIVE_COMPILER_SOURCE_CORPUS_OK') == 1)
    report = {'schema': 'bl.native.direct-source-observation', 'version': 2,
        'status': 'pass' if passed else 'failed', 'scope': 'one actual Source gate; full fixpoint remains open',
        'deadline_seconds': 120, 'timeout': timed, 'exit': process.returncode,
        'seconds': round(time.monotonic() - start, 3), 'argv': argv, 'inputs': inputs,
        'inputs_unchanged': unchanged, 'cleanup': cleanup, 'source_or_anf_interpreter': False,
        'sdk_launched': False, 'route': build['route'], 'dynamic_witnesses': len(rows),
        'last_dynamic_witness': rows[-1] if rows else None, 'witness_valid': bool(witness_valid),
        'log': {'path': str(log), 'sha256': sha(log)}, 'original_bundle_suffix_byte_equal': True}
    (out / 'observation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: report[name] for name in ('status', 'seconds', 'timeout', 'exit', 'dynamic_witnesses')}), flush=True)
    print(output[-3000:], flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
