#!/usr/bin/env python3
"""Prepare a fixed linked-module observer; starts no VM, compiler or module."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HOST_SHA = 'd00c0c75a33cc4afc90315620d3039c48ed31464fdc0c32e5ac2841aa9d1ab8a'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


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

    def load_data(path, limit=1048576):
        path = Path(path).resolve()
        bind(path)
        if path.stat().st_size > limit:
            raise RuntimeError('probe DATA exceeds its byte bound')
        return json.loads(path.read_text())

    data = load_data(capture)
    if (data.get('schema') != 'bl.native.linked-module-proof' or data.get('version') != 1
            or not all(isinstance(data.get(name), str) for name in ('provider', 'consumer'))
            or len(data.get('versions', [])) != 2):
        raise RuntimeError('requires the two-linked-module BL owner handoff')
    prototype = data.get('prototype')
    if prototype not in (None, 'reader-ignored-char-v1'):
        raise RuntimeError('unsupported closed linked prototype')
    reader_vertical = prototype == 'reader-ignored-char-v1'
    bind(data['producer']['path'], data['producer']['sha256'])
    if reader_vertical:
        bind(data['fixture-config']['path'], data['fixture-config']['sha256'])
    qualified = load_data(compiler / 'full-native-build.json', limit=32 * 1024 * 1024)
    if (qualified.get('schema') != 'bl.native.full-bounded-build' or qualified.get('version') != 1
            or qualified.get('status') != 'qualified' or qualified.get('compile_deadline_seconds') != 120):
        raise RuntimeError('native host must retain its qualified compiler receipt')
    for path, expected in qualified['inputs'].items():
        selected = Path(path)
        bind(selected if selected.is_absolute() else base / selected, expected)
    bind(data['sdk']['descriptor']['path'], data['sdk']['descriptor']['sha256'])
    stage = next(row for row in qualified['builds'] if row['stage'] == 'stage1')
    host, source, image, bundle = (compiler / name for name in ('host.scm', 'stage1.scm', 'stage1', 'bundle.scm'))
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
    spec = importlib.util.spec_from_file_location('native_linked_transport', bridge)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    bind(data['tool_request'], data['tool_request_sha256'])
    request = load_data(data['tool_request'])
    identity, _, tool_inputs, _ = transport.capture(request, base)
    for path, expected in tool_inputs.items():
        bind(path, expected)
    if not any((row['role'] == 'host-abi' or row['role'].startswith('host-abi/'))
               and row['sha256'] == HOST_SHA for row in identity['code_inputs']):
        raise RuntimeError('target ABI does not bind the qualified native host Source')

    def module(row, namespace, definitions):
        bind(row['fixture']['path'], row['fixture']['sha256'])
        receipt_path = Path(row['receipt']).resolve()
        bind(receipt_path, row['receipt_sha256'])
        verified = transport.verify_receipt(receipt_path, row['selection_key'], identity)
        for member in verified['artifacts'].values():
            bind(receipt_path.parent / member['file'], member['sha256'])
        bind(row['emission'], row['emission_sha256'])
        emission = load_data(row['emission'])
        if (emission.get('unit-id') != row['selection_key']
                or emission.get('namespaces') != [namespace]
                or not isinstance(emission.get('initializer'), str)
                or not isinstance(emission.get('provided-mfas'), list)
                or not emission['provided-mfas']):
            raise RuntimeError('linked module lacks exact namespace/initializer/MFA metadata')
        selected = {}
        for name, arity in definitions:
            exports = [entry for entry in emission['exports']
                       if entry.get('namespace') == namespace and entry.get('name') == name]
            if len(exports) != 1 or arity not in exports[0]['fixed']:
                raise RuntimeError('linked module lacks exact expected public callable')
            physical = [entry['scheme-global'] for entry in exports[0]['physical']]
            if not physical or any(not isinstance(value, str) for value in physical):
                raise RuntimeError('linked module lacks actual physical function bindings')
            selected[name] = physical
        return {'module': receipt_path.parent / verified['artifacts']['module']['file'],
                'module_name': verified['module_name'], 'selection_key': row['selection_key'],
                'initializer': emission['initializer'], 'physical': selected}

    versions = []
    for row in data['versions']:
        versions.append({
            'provider': module(row['provider'], data['provider'],
                [('make-helper', 1), ('make-tagged', 1)] if reader_vertical else [('answer', 0), ('adder', 1)]),
            'consumer': module(row['consumer'], data['consumer'],
                [('make-helper', 1), ('make-tagged', 1)] if reader_vertical else [('answer', 0), ('capture', 1)]),
        })
    if len({entry['module_name'] for row in versions for entry in row.values()}) != 4:
        raise RuntimeError('requires separately emitted distinct provider and consumer revisions')
    planner = data['planner']
    if (planner.get('owner') != 'build-plan/key-for' or planner.get('selected') != [data['provider']]
            or planner['before'][data['consumer']] != planner['after'][data['consumer']]
            or planner['before'][data['provider']] == planner['after'][data['provider']]
            or planner.get('consumer-artifact-reused') is not False):
        raise RuntimeError('requires explicit shared planner vs exact artifact distinction')
    template = here.parent / 'vertical/reader-proof.scm.in' if reader_vertical else here.with_name('linked-proof.scm.in')
    bind(template)
    bind(here)
    text = template.read_text()
    vertical_identity = None
    if reader_vertical:
        # Existing native procedure/physical owner checks, no alternate loader.
        helpers = here.with_name('linked-proof.scm.in')
        bind(helpers)
        text = helpers.read_text().split('(define linked-provider @PROVIDER@)')[0] + text
        theorem = data['scalar-gate']
        for field in ('receipt', 'candidate', 'proof-artifact', 'original-source', 'partition', 'manifest'):
            bind(theorem[field]['path'], theorem[field]['sha256'])
        corpus = base / 'benchmark/compiler-values.bl'
        bind(corpus)
        original_pin = load_data(base / 'sdk-pin.json')
        kernel = Path(original_pin['source']) / 'priv/boot/rt.bl'
        reader = Path(original_pin['source']) / 'priv/boot/reader.bl'
        kernel_sha, reader_sha = bind(kernel), bind(reader)
        text = text.replace('@CORPUS_SOURCE@', scheme_string(corpus.read_text()))
        text = text.replace('@IMAGE_SHA@', scheme_string(stage['executable_sha256']))
        text = text.replace('@KERNEL_SHA@', scheme_string(kernel_sha))
        for label, row in zip(('FIRST', 'SECOND'), versions):
            text = text.replace('@' + label + '_PROVIDER_STAMP@', scheme_string(row['provider']['selection_key']))
        vertical_identity = {'image': stage['executable_sha256'],
            'kernel_source': {'path': str(kernel), 'sha256': kernel_sha},
            'reader_source': {'path': str(reader), 'sha256': reader_sha},
            'corpus': {'path': str(corpus), 'sha256': sha(corpus)},
            'provider_revision_labels': {str(i + 1): row['provider']['selection_key'] for i, row in enumerate(versions)},
            'request_scope': 'closed serial Source read only; no arbitrary callbacks/concurrent publication',
            'image_admission': 'original complete receipt; per-request actual compiled binding/parent checks',
            'native_retirement_claimed': False}
    text = text.replace('@PROVIDER@', scheme_string(data['provider']))
    text = text.replace('@CONSUMER@', scheme_string(data['consumer']))
    out.mkdir(parents=True)
    invalid = out / 'invalid-module.o1'
    invalid.write_bytes(b'\x7fELF deliberately malformed linked-probe module\n')
    text = text.replace('@INVALID_MODULE@', scheme_string(str(invalid)))
    for label, row in zip(('FIRST', 'SECOND'), versions):
        for role, record in row.items():
            prefix = '@' + label + '_' + role.upper() + '_'
            text = text.replace(prefix + 'MODULE@', scheme_string(str(record['module'])))
            text = text.replace(prefix + 'INITIALIZER@', scheme_string(record['initializer']))
            for name, physical in record['physical'].items():
                literal = '(' + ' '.join(scheme_string(value) for value in physical) + ')'
                text = text.replace(prefix + name.upper() + '_PHYSICAL@', literal)
    if any(marker in text for marker in ('@FIRST_', '@SECOND_', '@PROVIDER@', '@CONSUMER@', '@INVALID_MODULE@')):
        raise RuntimeError('linked observer retained unresolved DATA placeholders')
    prefix = text.encode()
    original = bundle.read_bytes()
    observer = out / 'probe-bundle.scm'
    observer.write_bytes(prefix + b'\n' + original)
    result = {'schema': 'bl.native.linked-module-probe-preparation', 'version': 1,
              'status': 'prepared-not-executed', 'qualification': False,
              'scope': 'separate compiled provider/consumer late-link/capture/GC and pre-init failure; no generation custody',
              'inputs': inputs, 'output': {'path': str(observer), 'sha256': sha(observer)},
              'invalid_module': {'path': str(invalid), 'sha256': sha(invalid)},
              'original_bundle_suffix_byte_equal': observer.read_bytes()[len(prefix) + 1:] == original,
              'checks': None if reader_vertical else 36, 'argv': [str(image), '--eval', str(observer), str(bundle)],
              'runtime_deadline_seconds': 60 if reader_vertical else 20,
              'native_module_names': [entry['module_name'] for row in versions for entry in row.values()],
              'sdk_or_runtime_launched_by_preparer': False, 'generation_custody': False,
              'vertical_identity': vertical_identity}
    (out / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['argv']), flush=True)


if __name__ == '__main__':
    main()
