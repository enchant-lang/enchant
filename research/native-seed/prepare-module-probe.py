#!/usr/bin/env python3
"""Prepare a two-revision native module probe; starts no VM or compiler."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HOST_SHA = 'd00c0c75a33cc4afc90315620d3039c48ed31464fdc0c32e5ac2841aa9d1ab8a'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def scheme_string(value):
    escapes = {'\\': '\\\\', '"': '\\"', '\n': '\\n', '\r': '\\r', '\t': '\\t'}
    return '"' + ''.join(escapes.get(c, '\\x' + format(ord(c), 'x') + ';'
                       if ord(c) < 32 or ord(c) == 127 else c) for c in value) + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-dir', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    compiler, capture, out = (p.resolve() for p in (args.compiler_dir, args.capture, args.out))
    if out.exists():
        parser.error('choose a fresh probe directory')
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = sha(path)
        if (expected is not None and actual != expected) or (
                str(path) in inputs and inputs[str(path)] != actual):
            raise RuntimeError('probe input differs: ' + str(path))
        inputs[str(path)] = actual
        return actual

    def load_data(path):
        path = Path(path).resolve()
        bind(path)
        if path.stat().st_size > 1048576:
            raise RuntimeError('probe DATA exceeds its byte bound')
        return json.loads(path.read_text())

    data = load_data(capture)
    if (data.get('schema') != 'bl.native.scheme-module-proof' or data.get('version') != 1
            or not isinstance(data.get('namespace'), str) or len(data.get('versions', [])) != 2):
        raise RuntimeError('requires the two-revision BL-owned module proof handoff')
    bind(data['producer']['path'], data['producer']['sha256'])
    qualified_path = compiler / 'full-native-build.json'
    qualified = load_data(qualified_path)
    if (qualified.get('schema') != 'bl.native.full-bounded-build' or qualified.get('version') != 1
            or qualified.get('status') != 'qualified' or qualified.get('compile_deadline_seconds') != 120):
        raise RuntimeError('native host must retain its qualified compiler receipt')
    for path, expected in qualified['inputs'].items():
        selected = Path(path)
        bind(selected if selected.is_absolute() else base / selected, expected)
    if 'sdk' in data:
        bind(data['sdk']['descriptor']['path'], data['sdk']['descriptor']['sha256'])
    stage = next(row for row in qualified['builds'] if row['stage'] == 'stage1')
    host, source, image, bundle = (compiler / name for name in
                                  ('host.scm', 'stage1.scm', 'stage1', 'bundle.scm'))
    bind(host, HOST_SHA)
    bind(source, stage['source_sha256'])
    bind(image, stage['executable_sha256'])
    bind(bundle)
    with image.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            raise RuntimeError('qualified compiler is not the actual native ELF')
    bridge = base / 'native_module.py'
    bind(bridge)
    bind(base / 'native_elf.py')
    sys.path.insert(0, str(base))
    spec = importlib.util.spec_from_file_location('native_module_probe_transport', bridge)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    bind(data['tool_request'], data['tool_request_sha256'])
    request = load_data(data['tool_request'])
    identity, _, tool_inputs, _ = transport.capture(request, base)
    for path, expected in tool_inputs.items():
        bind(path, expected)
    if not any((row['role'] == 'host-abi' or row['role'].startswith('host-abi/'))
               and row['sha256'] == HOST_SHA for row in identity['code_inputs']):
        raise RuntimeError('module target ABI does not bind the qualified native host Source')

    def version(row, fixtures=True):
        if fixtures:
            bind(row['fixture']['path'], row['fixture']['sha256'])
        receipt_path = Path(row['receipt']).resolve()
        bind(receipt_path, row['receipt_sha256'])
        receipt = load_data(receipt_path)
        if receipt['selection_key'] != row['selection_key']:
            raise RuntimeError('transport key differs from the BL artifact owner handoff')
        verified = transport.verify_receipt(receipt_path, receipt['selection_key'], identity)
        for member in verified['artifacts'].values():
            bind(receipt_path.parent / member['file'], member['sha256'])
        bind(row['emission'], row['emission_sha256'])
        emission = load_data(row['emission'])
        if (emission.get('unit-id') != row['selection_key']
                or not isinstance(emission.get('initializer'), str)
                or not isinstance(emission.get('exports'), list)):
            raise RuntimeError('module emission lacks its declared initializer/exports')
        selected = {}
        for name, arity in (('answer', 0), ('adder', 1)):
            exports = [entry for entry in emission['exports'] if entry.get('namespace') == data['namespace']
                       and entry.get('name') == name]
            if len(exports) != 1 or arity not in exports[0]['fixed']:
                raise RuntimeError('module emission lacks the exact expected public callable')
            physical = [entry['scheme-global'] for entry in exports[0]['physical']]
            if not physical or any(not isinstance(name, str) for name in physical):
                raise RuntimeError('module emission lacks actual physical function bindings')
            selected[name] = physical
        module = receipt_path.parent / verified['artifacts']['module']['file']
        return {'module': module, 'receipt': receipt_path, 'data': verified,
                'initializer': emission['initializer'], 'physical': selected}

    versions = [version(row) for row in data['versions']]
    if (versions[0]['data']['module_name'] == versions[1]['data']['module_name']
            or versions[0]['data']['selection_key'] == versions[1]['data']['selection_key']):
        raise RuntimeError('changed Source revisions need distinct native module identities')
    independent = version(data['independent'], fixtures=False)
    if independent['data'] != versions[0]['data']:
        raise RuntimeError('independently compiled/reused native artifact DATA differs')
    for role, member in versions[0]['data']['artifacts'].items():
        other = independent['data']['artifacts'][role]
        if (member != other or
                (versions[0]['receipt'].parent / member['file']).read_bytes() !=
                (independent['receipt'].parent / other['file']).read_bytes()):
            raise RuntimeError('independent native member bytes differ: ' + role)
    template = base / 'fixtures/scheme-module-proof.scm.in'
    bind(template)
    text = template.read_text().replace('@NAMESPACE@', scheme_string(data['namespace']))
    for label, record in zip(('FIRST', 'SECOND'), versions):
        text = text.replace('@' + label + '_MODULE@', scheme_string(str(record['module'])))
        text = text.replace('@' + label + '_INITIALIZER@', scheme_string(record['initializer']))
        for name in ('answer', 'adder'):
            literal = '(' + ' '.join(scheme_string(value) for value in record['physical'][name]) + ')'
            text = text.replace('@' + label + '_' + name.upper() + '_PHYSICAL@', literal)
    if '@FIRST_' in text or '@SECOND_' in text or '@NAMESPACE@' in text:
        raise RuntimeError('native module probe retained an unresolved DATA placeholder')
    prefix = text.encode()
    original = bundle.read_bytes()
    out.mkdir(parents=True)
    observer = out / 'probe-bundle.scm'
    observer.write_bytes(prefix + b'\n' + original)
    result = {'schema': 'bl.native.scheme-module-probe-preparation', 'version': 1,
              'status': 'prepared-not-executed', 'qualification': False,
              'scope': 'native two-revision module/capture/GC ABI; no Source/compiler fixpoint claim',
              'inputs': inputs, 'output': {'path': str(observer), 'sha256': sha(observer)},
              'original_bundle_suffix_byte_equal': observer.read_bytes()[len(prefix) + 1:] == original,
              'independent_native_members_byte_equal': True, 'checks': 18,
              'argv': [str(image), '--eval', str(observer), str(bundle)],
              'runtime_deadline_seconds': 20, 'native_module_names': [v['data']['module_name'] for v in versions],
              'sdk_or_runtime_launched_by_preparer': False}
    (out / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['argv']), flush=True)


if __name__ == '__main__':
    main()
