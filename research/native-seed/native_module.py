#!/usr/bin/env python3
"""Object-only tool transport for the existing BL artifact producer.

BL owns prepared plans, Source/phase selection, invalidation and artifact
membership. This adapter only reports pinned tool facts or builds/verifies a
declared Scheme module. No Source/ANF reader, planner or BL cache lives here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

import native_elf

SCHEMA = 'bl.native.scheme-tool-request'
RECEIPT = 'bl.native.scheme-native-module'
LIMIT = 1048576


def read_json(path):
    path = Path(path).resolve()
    if path.stat().st_size > LIMIT:
        raise RuntimeError('native tool DATA exceeds its byte bound')
    return json.loads(path.read_text())


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.writing')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def capture(request, base):
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        if str(path) in inputs:
            actual = inputs[str(path)]
        else:
            actual = native_elf.digest(path)
            inputs[str(path)] = actual
        if expected is not None and actual != expected:
            raise RuntimeError('native tool input differs: ' + str(path))
        return actual

    selected = Path(request['toolchain']).resolve()
    if selected != (base / 'toolchain-pin.json').resolve():
        raise RuntimeError('tool transport requires its exact pinned toolchain file')
    standard = request.get('standard_bindings', False)
    if type(standard) is not bool:
        raise RuntimeError('standard_bindings must be boolean')
    config = native_elf.configuration(base, standard, bind)
    bind(Path(__file__))
    tools = read_json(selected)
    gambit = Path(tools['gambit'])
    clang = Path(tools['clang'])
    fixed = [('gambit-compiler-code', gambit / 'gambit/lib/libgambitgsc.so'),
             ('gambit-interpreter-code', gambit / 'gambit/lib/libgambitgsi.so')]
    rows = request.get('code_inputs')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
        raise RuntimeError('declare the finite emitter, host ABI and native compiler code inputs')
    roles = set()
    declared = []
    by_role = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'role', 'path'}:
            raise RuntimeError('code input needs exactly role and path')
        role = row['role']
        if not isinstance(role, str) or not re.fullmatch('[A-Za-z0-9_.:/-]{1,200}', role) or role in roles:
            raise RuntimeError('code input roles must be unique finite names')
        path = Path(row['path']).resolve(strict=True)
        if not path.is_file():
            raise RuntimeError('code input is not a regular file')
        if role in {name for name, _ in fixed} or role.startswith('clang-support/'):
            raise RuntimeError('code input role collides with fixed tool facts')
        roles.add(role)
        by_role[role] = path
        declared.append((role, path))
    if (not {'clang-driver', 'clang-cpp', 'clang-core'}.issubset(roles)
            or not any(role == 'emitter' or role.startswith('emitter/') for role in roles)
            or not any(role == 'host-abi' or role.startswith('host-abi/') for role in roles)):
        raise RuntimeError('target identity omits emitter/host ABI/actual native compiler code')
    original_cc = clang / 'nix-support/orig-cc'
    bind(original_cc)
    actual_driver = (Path(original_cc.read_text().strip()) / 'bin/clang').resolve(strict=True)
    if by_role['clang-driver'] != actual_driver:
        raise RuntimeError('declared Clang driver differs from the pinned wrapper target')
    if (not by_role['clang-cpp'].name.startswith('libclang-cpp.so')
            or not by_role['clang-core'].name.startswith('libLLVM.so')):
        raise RuntimeError('declare the pinned native compiler libraries')
    support = sorted(path for path in (clang / 'nix-support').iterdir() if path.is_file())
    if len(support) > 128:
        raise RuntimeError('native compiler support inventory exceeds its bound')
    fixed.extend(('clang-support/' + path.name, path) for path in support)
    code = []
    for role, path in sorted(fixed + declared, key=lambda row: row[0]):
        code.append({'role': role, 'sha256': bind(path), 'bytes': path.stat().st_size})
    identity = {'schema': 'bl.native.scheme-target-tools', 'version': 1,
                'module_format': 'gambit-o1', 'route': 'c',
                'toolchain_sha256': bind(selected),
                'transport_sha256': bind(Path(__file__)),
                'process_helper_sha256': bind(base / 'check-self-emission.py'),
                'splitter_sha256': bind(config['splitter']),
                'tools': config['tool_identity'], 'code_inputs': code,
                'module_c_flags': [*config['flags'], '-D___DYNAMIC'],
                'module_link_flags': config['link_flags']}
    # Selection remains BL-owned. The object cache also binds this complete
    # target identity so changed emitter/runtime code cannot reuse an old recipe.
    config['tool_identity'] = {**config['tool_identity'], 'artifact_target': identity}
    return identity, config, inputs, bind


def local_member(directory, name):
    if not isinstance(name, str) or Path(name).name != name or name in ('', '.', '..'):
        raise RuntimeError('native module member must be one relative filename')
    path = directory / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('native module member is not an owned regular file')
    return path


def verify_receipt(path, selection, identity):
    path = Path(path).resolve()
    value = read_json(path)
    if (value.get('schema') != RECEIPT or value.get('version') != 1
            or value.get('selection_key') != selection or value.get('identity') != identity
            or value.get('native_admission') is not False):
        raise RuntimeError('native module receipt does not match the BL target selection')
    name = value.get('module_name')
    if not isinstance(name, str) or not re.fullmatch('bl[0-9a-f]{64}', name):
        raise RuntimeError('native module basename differs from its format')
    source_sha = value.get('source_sha256')
    if not isinstance(source_sha, str) or not re.fullmatch('[0-9a-f]{64}', source_sha):
        raise RuntimeError('native module source digest is invalid')
    expected_name = 'bl' + hashlib.sha256((selection + '\0' + source_sha).encode()).hexdigest()
    if name != expected_name:
        raise RuntimeError('native module is not named by selection and Scheme bytes')
    expected = {'source': name + '.scm', 'raw_c': name + '.c', 'c': name + '.dynamic.c',
                'module': name + '.o1', 'object_receipt': name + '.object.json'}
    if set(value['artifacts']) != set(expected):
        raise RuntimeError('native module member inventory differs')
    for role, filename in expected.items():
        row = value['artifacts'][role]
        if row['file'] != filename or native_elf.digest(local_member(path.parent, filename)) != row['sha256']:
            raise RuntimeError('native module artifact bytes differ: ' + role)
    if value['artifacts']['source']['sha256'] != source_sha:
        raise RuntimeError('native module source digest differs')
    module = local_member(path.parent, expected['module'])
    with module.open('rb') as stream:
        header = stream.read(18)
    if (len(header) != 18 or header[:4] != b'\x7fELF'
            or int.from_bytes(header[16:18], 'little' if header[5] == 1 else 'big') != 3):
        raise RuntimeError('native module is not an ELF shared object')
    proof = read_json(local_member(path.parent, expected['object_receipt']))
    request = proof['request']
    if (request.get('kind') != 'gambit-dynamic-module'
            or request.get('selection_key') != selection or request.get('module_name') != name
            or request.get('source_sha256') != source_sha
            or request.get('flags') != identity['module_c_flags']
            or request.get('tools') != {**identity['tools'], 'artifact_target': identity}
            or proof.get('linker_adapter') != {'from': '___LNK_' + name, 'to': '___LNK_' + name + '_2e_o1'}
            or any(proof['artifacts'].get(role) != value['artifacts'][role]['sha256']
                   for role in ('source', 'raw_c', 'c', 'module'))):
        raise RuntimeError('native module object receipt differs')
    raw = local_member(path.parent, expected['raw_c']).read_text()
    matches = list(re.finditer(r'^#define ___LINKER_ID ([^\s]+)[ \t]*$', raw, re.MULTILINE))
    if len(matches) != 1 or matches[0].group(1) != '___LNK_' + name:
        raise RuntimeError('native module raw C linker identity differs')
    match = matches[0]
    adapted = raw[:match.start()] + '#define ___LINKER_ID ___LNK_' + name + '_2e_o1' + raw[match.end():]
    if local_member(path.parent, expected['c']).read_text() != adapted:
        raise RuntimeError('native module C loader adapter changed more than its linker identity')
    return value



def build_module(folder, source, selection_key, config, *, cache, report, bind, run, save):
    """Compile one BL-emitted Scheme unit as a native, loadable Gambit module.

    The BL artifact owner supplies the complete unit and selection key. This
    transports bytes only: no Source/ANF parsing, dependency plan or BL cache.
    """
    import fcntl
    import re
    import shutil
    import time

    if not isinstance(source, bytes) or not source or len(source) > native_elf.HARD:
        raise RuntimeError('Scheme module exceeds the existing bounded unit limit')
    if not re.fullmatch('[0-9a-f]{64}', selection_key):
        raise RuntimeError('Scheme module requires the BL owner selection key')
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    source_sha = hashlib.sha256(source).hexdigest()
    # Alphanumeric names avoid target-name escaping. New versions have distinct
    # Gambit module identities even when retained closures outlive their caller.
    name = 'bl' + hashlib.sha256((selection_key + '\0' + source_sha).encode()).hexdigest()
    flags = [*config['flags'], '-D___DYNAMIC']
    request = {'kind': 'gambit-dynamic-module', 'source_sha256': source_sha,
               'selection_key': selection_key, 'module_name': name,
               'tools': config['tool_identity'], 'flags': flags}
    directory = Path(cache).resolve() / native_elf.key(request)
    directory.mkdir(parents=True, exist_ok=True)
    scm, raw, adapted, module = (directory / (name + suffix)
                                for suffix in ('.scm', '.c', '.dynamic.c', '.o1'))
    proof = directory / 'object.json'
    paths = {'source': scm, 'raw_c': raw, 'c': adapted, 'module': module}
    before, after = '___LNK_' + name, '___LNK_' + name + '_2e_o1'
    linker = {'from': before, 'to': after}
    lock = (directory / 'writer.lock').open('a')
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() - start >= native_elf.DEADLINE:
                lock.close()
                raise TimeoutError('native object cache writer exceeded its deadline')
            time.sleep(0.05)
    try:
        previous = json.loads(proof.read_text()) if proof.is_file() else {}
        reused = (previous.get('request') == request and previous.get('linker_adapter') == linker
                  and all(p.is_file() and native_elf.digest(p) == previous.get('artifacts', {}).get(role)
                          for role, p in paths.items()))
        if not reused:
            proof.unlink(missing_ok=True)
            scm.write_bytes(source)
            # Relative filenames keep cache/output directory locations out of
            # generated module names and the C compiler's input attribution.
            run('module-scheme-to-c',
                [config['gsc'], '-c', *config['scheme_flags'], '-o', raw.name, scm.name],
                cwd=directory, build=True)
            text = raw.read_text()
            matches = list(re.finditer(r'^#define ___LINKER_ID ([^\s]+)[ \t]*$', text, re.MULTILINE))
            if len(matches) != 1 or matches[0].group(1) != before:
                raise RuntimeError('Scheme C output has an unexpected module linker identity')
            match = matches[0]
            adapted.write_text(text[:match.start()] + '#define ___LINKER_ID ' + after
                               + text[match.end():])
            run('module-c-shared',
                [config['clang'], *flags, '-shared', '-rdynamic', adapted.name,
                 *config['link_flags'], '-o', module.name],
                cwd=directory, build=True)
            with module.open('rb') as stream:
                header = stream.read(18)
            if (header[:4] != b'\x7fELF' or len(header) != 18
                    or int.from_bytes(header[16:18], 'little' if header[5] == 1 else 'big') != 3):
                raise RuntimeError('Scheme module is not a native ELF shared object')
            previous = {'request': request, 'linker_adapter': linker,
                        'artifacts': {role: native_elf.digest(p) for role, p in paths.items()}}
            temporary = proof.with_suffix('.json.writing')
            temporary.write_text(json.dumps(previous, indent=2) + '\n')
            temporary.replace(proof)
        artifacts = {}
        for role, path in paths.items():
            bind(path, previous['artifacts'][role])
            target = folder / path.name
            if target != path:
                shutil.copy2(path, target)
            artifacts[role] = {'path': str(target), 'sha256': bind(target, previous['artifacts'][role])}
        target_proof = folder / (name + '.object.json')
        target_proof.write_text(json.dumps(previous, indent=2) + '\n')
        result = {'selection_key': selection_key, 'module_name': name,
                  'source_sha256': source_sha, 'reused': reused,
                  'linker_adapter': linker, 'artifacts': artifacts,
                  'object_receipt': {'path': str(target_proof), 'sha256': bind(target_proof)}}
        report['module'] = result
        save()
        return result
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('method', choices=('identity', 'build', 'verify'))
    parser.add_argument('request', type=Path)
    parser.add_argument('result', type=Path)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    request = read_json(args.request)
    if request.get('schema') != SCHEMA or request.get('version') != 1:
        raise RuntimeError('unsupported native tool request')
    identity, config, inputs, bind = capture(request, base)
    result = {'schema': 'bl.native.scheme-tool-result', 'version': 1, 'method': args.method,
              'status': 'failed', 'identity': identity, 'inputs': inputs,
              'jobs': [], 'native_admission': False}

    def save():
        save_json(args.result, result)

    try:
        if args.method == 'identity':
            result['status'] = 'identity'
        else:
            if request.get('expected_identity') != identity:
                raise RuntimeError('target tool/code identity changed after BL selection')
            selection = request.get('selection_key')
            if not isinstance(selection, str) or not re.fullmatch('[0-9a-f]{64}', selection):
                raise RuntimeError('BL selection_key must be a SHA256 string')
            if args.method == 'verify':
                receipt = Path(request['receipt']).resolve()
                if receipt.parent == args.result.resolve().parent or receipt.parent in args.result.resolve().parents:
                    raise RuntimeError('verification observations must be outside the artifact')
                verified = verify_receipt(receipt, selection, identity)
                result.update(status='verified-not-admitted', receipt=str(receipt),
                              receipt_sha256=native_elf.digest(receipt),
                              module_name=verified['module_name'], artifacts=verified['artifacts'])
            else:
                out = Path(request['out']).resolve()
                if out == args.result.resolve().parent or out in args.result.resolve().parents:
                    raise RuntimeError('build observations must be outside the artifact')
                source = Path(request['source']['path']).resolve()
                if source.stat().st_size > native_elf.HARD:
                    raise RuntimeError('Scheme module exceeds the existing bounded unit limit')
                bind(source, request['source']['sha256'])
                source_bytes = source.read_bytes()
                if hashlib.sha256(source_bytes).hexdigest() != request['source']['sha256']:
                    raise RuntimeError('Scheme module changed during capture')
                helper_path = base / 'check-self-emission.py'
                bind(helper_path)
                spec = importlib.util.spec_from_file_location('native_module_owned_tree', helper_path)
                helper = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(helper)
                out.mkdir(parents=True, exist_ok=True)
                observations = args.result.resolve().with_name(args.result.name + '.jobs')
                observations.mkdir(parents=True, exist_ok=True)

                def run(name, argv, cwd=None, build=False):
                    row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(cwd),
                           'deadline_seconds': native_elf.DEADLINE}
                    result['jobs'].append(row)
                    save()
                    log = observations / (name + '.log')
                    start, timed = time.monotonic(), False
                    with log.open('w') as stream:
                        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                        tree = helper.OwnedTree(process)
                        try:
                            while process.poll() is None:
                                tree.discover()
                                if time.monotonic() - start >= native_elf.DEADLINE:
                                    timed = True
                                    break
                                time.sleep(0.05)
                        finally:
                            cleanup = tree.cleanup()
                    row.update(exit=process.returncode, timeout=timed,
                               seconds=time.monotonic() - start, cleanup=cleanup,
                               log={'path': str(log), 'sha256': native_elf.digest(log)})
                    save()
                    if timed or process.returncode != 0 or cleanup['errors']:
                        raise RuntimeError('native tool child failed: ' + name)

                module = build_module(out, source_bytes, selection, config,
                    cache=Path(request['cache']), report=result, bind=bind, run=run, save=save)
                artifacts = {role: {'file': Path(row['path']).name, 'sha256': row['sha256']}
                             for role, row in module['artifacts'].items()}
                artifacts['object_receipt'] = {'file': Path(module['object_receipt']['path']).name,
                                               'sha256': module['object_receipt']['sha256']}
                stable = {'schema': RECEIPT, 'version': 1, 'identity': identity,
                          'selection_key': selection, 'source_sha256': module['source_sha256'],
                          'module_name': module['module_name'], 'artifacts': artifacts,
                          'native_admission': False}
                receipt = out / 'native-module.json'
                save_json(receipt, stable)
                verify_receipt(receipt, selection, identity)
                result.update(status='compiled-not-admitted', receipt=str(receipt),
                              receipt_sha256=native_elf.digest(receipt))
        unchanged = all(Path(path).is_file() and native_elf.digest(path) == expected
                        for path, expected in inputs.items())
        result['inputs_unchanged'] = unchanged
        if not unchanged:
            raise RuntimeError('native tool/code input changed during transport')
    except BaseException as error:
        result.update(status='failed', error=str(error))
        raise
    finally:
        save()
    print('NATIVE_SCHEME_TOOL_' + args.method.upper() + '_OK', flush=True)


if __name__ == '__main__':
    main()
