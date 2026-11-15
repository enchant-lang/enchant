#!/usr/bin/env python3
"""Build/reuse the exact GVM host cache, then check its C and LLVM host ABI.

Run inside a cgroup capped at 3GiB. Jobs are serial and each keeps 120s.
No Source profile, producer, Source evaluator or GVM program is admitted here.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


LOADER_FIXTURE_SHA256 = '8cdf529cccbb11a92701fda367bcd70e02daf85d67a59cdaa71e2c2eb1af5c91'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def memory_admission():
    rows = [row.split(':', 2) for row in Path('/proc/self/cgroup').read_text().splitlines()]
    unified = next((row[2] for row in rows if row[:2] == ['0', '']), None)
    if unified is None:
        raise RuntimeError('host check requires unified cgroup memory admission')
    root = Path('/sys/fs/cgroup')
    selected = root / unified.lstrip('/')
    observed = []
    while True:
        path = selected / 'memory.max'
        if path.is_file():
            value = path.read_text().strip()
            observed.append({'path': str(path), 'bytes': int(value) if value != 'max' else None})
        if selected == root:
            break
        if root not in selected.parents:
            raise RuntimeError('unexpected cgroup namespace path')
        selected = selected.parent
    bounds = [row['bytes'] for row in observed if row['bytes'] is not None]
    if not bounds or min(bounds) > 3 * 1024**3:
        raise RuntimeError('run under systemd-run --user --collect --wait --property=MemoryMax=3G '
                           '--property=MemorySwapMax=0; no compiler was started')
    return {'maximum_bytes': min(bounds), 'observed': observed}


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=Path, default=base / 'out/gvm-host-v1')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=root / '.local/native-gvm-build-cache')
    parser.add_argument('--fixture', type=Path, default=base / 'gvm/loader-check.scm')
    args = parser.parse_args()
    host, out, cache, fixture = (p.resolve() for p in
                               (args.host, args.out, args.cache, args.fixture))
    if out.exists():
        parser.error('choose a fresh host-check output directory')
    memory = memory_admission()
    builder_path = base / 'gvm/build-profile.py'
    builder = load('pinned_gvm_profile_recipe', builder_path)
    tree_helper = load('host_check_owned_tree', base / 'check-self-emission.py')
    decode = load('host_check_owned_metadata', base / 'gvm/read-metadata.py').decode
    source = host / 'host.scm'
    ledger_json = host / 'host.components.json'
    ledger_scm = host / 'host.components.scm'
    ledger = json.loads(ledger_json.read_text())
    source_ledger = decode(ledger_scm.read_text())
    expected = {'schema': ledger.get('schema'), 'version': ledger.get('version'),
                'runtime-abi': ledger.get('runtime-abi'),
                'source-sha256': ledger.get('source_sha256'), 'components': ledger.get('components')}
    if (ledger.get('schema') != 'bl.native.gvm-host' or ledger.get('version') != 1
            or ledger.get('runtime-abi') != 1 or builder.sha(source) != ledger['source_sha256']
            or source_ledger != expected):
        raise RuntimeError('host source and owned ledgers differ')
    if (builder.sha(fixture) != LOADER_FIXTURE_SHA256
            or fixture.read_text().count('GVM_LOADER_HOST_ABI_PASS 27') != 1):
        raise RuntimeError('requires the exact 27-check loader ABI fixture')
    tools_path = base / 'toolchain-pin.json'
    tools = json.loads(tools_path.read_text())
    gambit, clang = Path(tools['gambit']), str(Path(tools['clang']) / 'bin/clang')
    gsc, runtime = str(gambit / 'bin/gsc'), gambit / 'gambit/lib/libgambit.so'
    # EXACT copy of build_profile's host request, key and receipt schema.
    # Workflow-only checks/provenance do not enter the object cache request.
    environment = builder.key({k: v for k, v in os.environ.items()
                               if k in ('PATH', 'LD_LIBRARY_PATH') or k.startswith('NIX_')})
    request = {'source': builder.sha(source), 'tools': tools, 'flags': builder.FLAGS,
               'environment': environment, 'runtime': builder.sha(runtime),
               'recipe': hashlib.sha256(inspect.getsource(builder.compile_host).encode()).hexdigest()}
    directory = cache / 'hosts' / builder.key(request)
    receipt_path = directory / 'receipt.json'
    inputs = {str(p): builder.sha(p) for p in
              (here, builder_path, base / 'gvm/build-module.py', base / 'gvm/read-metadata.py',
               base / 'check-self-emission.py', tools_path, source, ledger_json, ledger_scm, fixture)}
    out.mkdir(parents=True)
    cache.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'bl.native.gvm-host-check', 'version': 1, 'status': 'building',
              'scope': 'shared native host loader ABI only; no Source/GVM program qualification',
              'source_profile_admitted': False, 'sdk_launched': False,
              'runtime-abi': 1, 'memory': memory, 'child_deadline_seconds': 120,
              'inputs': inputs, 'tools': tools, 'host_request': request,
              'host_cache': str(directory), 'jobs': [], 'routes': {}}

    def save():
        (out / 'host-check.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(name, argv, cwd, timeout=120):
        if timeout != 120:
            raise RuntimeError('host child must keep the exact 120s deadline')
        log = out / (name + '.log')
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(cwd),
               'deadline_seconds': 120}
        report['jobs'].append(row)
        save()
        start, timed = time.monotonic(), False
        with log.open('w') as stream:
            process = subprocess.Popen(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
            tree = tree_helper.OwnedTree(process)
            try:
                while process.poll() is None:
                    tree.discover()
                    if time.monotonic() - start >= 120:
                        timed = True
                        break
                    time.sleep(0.1)
            finally:
                cleanup = tree.cleanup()
                row.update(returncode=process.returncode, timeout=timed,
                           seconds=time.monotonic() - start, cleanup=cleanup,
                           log={'path': str(log), 'sha256': builder.sha(log)})
                save()
        if timed or process.returncode != 0 or cleanup['errors']:
            raise RuntimeError(name + ' failed: ' + str(log))

    lock = (cache / 'writer.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if receipt['request'] != request or any(builder.sha(p) != h for p, h in receipt['artifacts'].items()):
                raise RuntimeError('immutable native host cache differs')
            report['reused'] = True
        else:
            directory.mkdir(parents=True, exist_ok=True)
            paths = builder.compile_host(source, directory, gambit, clang, gsc, run)
            receipt = {'request': request, 'artifacts': {str(p): builder.sha(p) for p in paths}}
            receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
            report['reused'] = False
        report['receipt'] = builder.record(receipt_path)
        report['host_artifacts'] = receipt['artifacts']
        save()
        # Release the build lock before read-only host execution. Both objects
        # and their sealed receipt are independently verified before/after.
    except BaseException as error:
        report.update(status='failed', error=str(error))
        save()
        raise
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    try:
        for route, selected in (('c', directory / 'host.o1'), ('llvm', directory / 'llvm/host.o1')):
            target = out / route / 'host.o1'
            target.parent.mkdir()
            shutil.copy2(selected, target)
            expression = ('(with-exception-catcher '
                '(lambda (failure) (display-exception failure) (newline) (exit 1)) '
                '(lambda () (load ' + json.dumps(str(target)) + ') '
                '(if (##interp-procedure? native-gvm-publish-loaded!) '
                '(error "GVM host publisher is interpreted")) '
                '(load ' + json.dumps(str(fixture)) + ') (exit 0)))')
            run(route + '-loader-abi', [str(gambit / 'bin/gsi'), '-e', expression], root)
            log = out / (route + '-loader-abi.log')
            if log.read_text(errors='replace').splitlines().count('GVM_LOADER_HOST_ABI_PASS 27') != 1:
                raise RuntimeError(route + ' lacks the exact 27-check loader ABI result')
            report['routes'][route] = {'status': 'host-abi-pass', 'checks': 27,
                                       'module': builder.record(target),
                                       'log': builder.record(log)}
            save()
        unchanged = all(Path(p).is_file() and builder.sha(p) == h for p, h in inputs.items())
        artifacts_unchanged = all(Path(p).is_file() and builder.sha(p) == h
                                  for p, h in receipt['artifacts'].items())
        report.update(inputs_unchanged=unchanged, artifacts_unchanged=artifacts_unchanged)
        if not unchanged or not artifacts_unchanged:
            raise RuntimeError('host build/check input or sealed artifact changed')
        report['status'] = 'host-abi-pass'
        print('GVM_HOST_C_AND_LLVM_LOADER_ABI_PASS 27', flush=True)
    except BaseException as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
