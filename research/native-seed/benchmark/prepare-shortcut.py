#!/usr/bin/env python3
"""Bind one actual AOT module to the existing qualified compiler observer."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--preparation', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    base = here.parent
    sys.path.insert(0, str(base))
    transport = module(base / 'native_module.py', 'shortcut_transport')
    literals = module(here / 'prepare-benchmark.py', 'shortcut_literals')
    sha = literals.digest
    parent = json.loads(args.preparation.read_text())
    assert parent['schema'] == 'bl.native.warm-core-benchmark-preparation'
    inputs = dict(parent['inputs'])
    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = sha(path)
        assert expected is None or actual == expected, str(path)
        assert str(path) not in inputs or inputs[str(path)] == actual, str(path)
        inputs[str(path)] = actual
        return actual
    for path, expected in list(inputs.items()):
        bind(path, expected)
    bind(args.preparation)
    bind(__file__)
    bind(args.module)
    data = json.loads(args.module.read_text())
    assert data['schema'] == 'bl.native.equality-shortcut-module' and data['compiled']
    for field in ['source', 'receipt', 'exports', 'request']:
        bind(data[field]['path'], data[field]['sha256'])
    bind(data['original']['source']['path'], data['original']['source']['sha256'])
    request = json.loads(Path(data['request']['path']).read_text())
    identity, _, tool_inputs, _ = transport.capture(request, base)
    for path, expected in tool_inputs.items():
        bind(path, expected)
    verified = transport.verify_receipt(Path(data['receipt']['path']), data['selection-key'], identity)
    directory = Path(data['directory'])
    for member in verified['artifacts'].values():
        bind(directory / member['file'], member['sha256'])
    exports = json.loads(Path(data['exports']['path']).read_text())
    selected = [row for row in exports['exports'] if row['namespace'] == data['namespace'] and row['name'] == 'make-helper']
    assert len(selected) == 1 and selected[0]['fixed'] == [1]
    physical = selected[0]['physical']
    assert physical
    observer = parent['native']['observer']
    bind(observer['path'], observer['sha256'])
    original = Path(parent['native']['argv'][3]).read_bytes()
    observed = Path(observer['path']).read_bytes()
    assert observed.endswith(b'\n' + original)
    prefix = observed[:-len(original)-1].decode().split('(define (bench-run)\n')[0]
    helpers = base / 'linked-proof.scm.in'
    bind(helpers)
    template = here / 'shortcut.scm.in'
    bind(template)
    text = template.read_text()
    assert not args.out.exists()
    args.out.mkdir(parents=True)
    values = {'MODULE': str(directory / verified['artifacts']['module']['file']),
              'INITIALIZER': exports['initializer'], 'NAMESPACE': data['namespace'],
              'OUTPUT': str(args.out.resolve()),
              'PHYSICAL': '(' + ' '.join(literals.scheme_string(row['scheme-global']) for row in physical) + ')'}
    for key, value in values.items():
        text = text.replace('@' + key + '@', value if key == 'PHYSICAL' else literals.scheme_string(value))
    assert all('@' + key + '@' not in text for key in values)
    observer_path = args.out / 'observer.scm'
    helper_prefix = helpers.read_text().split('(define linked-provider @PROVIDER@)')[0]
    observer_path.write_bytes((helper_prefix + prefix + text).encode() + b'\n' + original)
    report = {'schema': 'bl.native.equality-shortcut-preparation', 'version': 1,
              'inputs': inputs, 'observer': {'path': str(observer_path.resolve()), 'sha256': sha(observer_path)},
              'argv': [parent['native']['argv'][0], '--eval', str(observer_path.resolve()), parent['native']['argv'][3]],
              'deadline_seconds': 60, 'samples': 5, 'repetitions': 5,
              'original_image_reused': True, 'original_bundle_suffix_byte_equal': observer_path.read_bytes().endswith(b'\n' + original),
              'qualification': False, 'native_runtime_admission': False, 'native_lowering_proof': False}
    (args.out / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('EQUALITY_SHORTCUT_PREPARED')


if __name__ == '__main__':
    main()
