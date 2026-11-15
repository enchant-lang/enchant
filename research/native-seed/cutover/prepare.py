#!/usr/bin/env python3
"""Verify existing owners' receipts; construct only the observation harness."""
import argparse, importlib.util, json, sys
from pathlib import Path

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('modules', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    base = here.parent
    sys.path.insert(0, str(base))
    transport = load(base / 'native_module.py', 'cutover_transport')
    literals = load(base / 'benchmark/prepare-benchmark.py', 'cutover_literals')
    sha, quoted = literals.digest, literals.scheme_string
    inputs = {}
    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = inputs.get(str(path)) or sha(path)
        if expected is not None and actual != expected:
            raise RuntimeError('changed input: ' + str(path))
        inputs[str(path)] = actual
        return actual
    receipt_path = base / 'out/compiler-native-owner/full-native-build.json'
    bind(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'qualified'
    historical = []
    # Reuse the qualified image as an artifact. Executing it does not read
    # its historical C/object inputs. Bind its exact producer Source snapshot,
    # executable and original bundle; do not rehash/rebuild discarded stages.
    emitter = base / 'src/native/scheme.bl'
    expected = receipt['inputs'][str(emitter)]
    old = here / 'frozen-emitter.source'
    bind(old, expected)
    historical.append({'original_path': str(emitter), 'frozen_bytes': str(old), 'sha256': expected})
    stage = next(row for row in receipt['builds'] if row['stage'] == 'stage1')
    image = base / 'out/compiler-native-owner/stage1'
    bind(image, stage['executable_sha256'])
    bind(base / 'src/native/scheme.bl')
    for path in [Path(__file__), args.modules, here / 'observer.scm.in', base / 'linked-proof.scm.in',
                 base / 'benchmark/native-observer.scm.in', base / 'benchmark/compiler-values.bl']:
        bind(path)
    data = json.loads(args.modules.read_text())
    assert data['schema'] == 'bl.native.cutover-modules'
    for field in ['source', 'derived']:
        bind(data[field]['path'], data[field]['sha256'])
    replacements = {'NAMESPACE': quoted(data['namespace']), 'OUTPUT': quoted(str(args.output.resolve()))}
    inventories = []
    verification_environments = []
    captured = {}
    runtime_inputs = {str(image): sha(image)}
    for row in data['modules']:
        request = json.loads(Path(row['request']).read_text())
        request_key = json.dumps(request, sort_keys=True)
        if request_key not in captured:
            captured[request_key] = transport.capture(request, base)
        original_identity, _, tool_inputs, _ = captured[request_key]
        current_identity = json.loads(json.dumps(original_identity))
        identity_path = Path(row['request']).with_name(Path(row['request']).name.replace('-request.json', '-result.json'))
        bind(row['request'])
        bind(identity_path)
        identity = json.loads(identity_path.read_text())['identity']
        # This is read-only artifact verification, not a new compiler run.
        # Keep the recorded build environment in the recipe; independently
        # compare every actual tool/Source byte and other configuration field.
        observed_env = current_identity['tools']['compiler_environment_sha256']
        built_env = identity['tools']['compiler_environment_sha256']
        verification_environments.append({'mode': row['mode'], 'build': built_env, 'verification': observed_env})
        current_identity['tools']['compiler_environment_sha256'] = built_env
        assert identity == current_identity, 'tool or producer identity changed'
        for path, expected in tool_inputs.items():
            bind(path, expected)
        directory = Path(row['directory'])
        receipt = transport.verify_receipt(directory / 'native-module.json', row['selection-key'], identity)
        for member in receipt['artifacts'].values():
            bind(directory / member['file'], member['sha256'])
        module_member = receipt['artifacts']['module']
        runtime_inputs[str(directory / module_member['file'])] = module_member['sha256']
        exports_path = directory / 'exports.json'
        bind(exports_path)
        exports = json.loads(exports_path.read_text())
        label = 'REFERENCE' if row['mode'] == 'reference' else 'CANDIDATE'
        replacements[label + '_MODULE'] = quoted(str(directory / receipt['artifacts']['module']['file']))
        replacements[label + '_INITIALIZER'] = quoted(exports['initializer'])
        replacements[label + '_CHECK'] = quoted(exports['primitive-check'])
        replacements[label + '_PHYSICAL'] = '(' + ' '.join(quoted(p['scheme-global']) for e in exports['exports'] for p in e['physical']) + ')'
        inventories.append({'mode': row['mode'], 'counts': exports['emission-counts'],
                            'primitive_mfas': exports['primitive-mfas'], 'exports': len(exports['exports'])})
        if label == 'CANDIDATE':
            assert exports['emission-counts']['compiled-pattern-clauses'] > 0
            assert exports['emission-counts']['direct-primitive-calls'] > 0
            replacements['GUARD_KEY'] = quoted(exports['primitive-mfas'][0])
    assert len(inventories) == 2
    bundle = base / 'out/compiler-native-owner/bundle.scm'
    runtime_inputs[str(bundle)] = bind(bundle)
    helper = (base / 'linked-proof.scm.in').read_text().split('(define linked-provider @PROVIDER@)')[0]
    observer = (base / 'benchmark/native-observer.scm.in').read_text().split('(define (bench-run)\n')[0]
    observer = observer.replace('@SOURCE@', quoted((base / 'benchmark/compiler-values.bl').read_text()))
    text = (here / 'observer.scm.in').read_text()
    for key, value in replacements.items():
        text = text.replace('@' + key + '@', value)
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    path = args.output / 'observer.scm'
    path.write_bytes((helper + observer + text).encode() + b'\n' + bundle.read_bytes())
    report = {'schema': 'bl.native.cutover-preparation', 'inputs': inputs, 'historical_source_bindings': historical,
              'observer': {'path': str(path.resolve()), 'sha256': sha(path)}, 'inventories': inventories,
              'verification_environments': verification_environments, 'runtime_inputs': runtime_inputs,
              'argv': [str(image), '--eval', str(path.resolve()), str(bundle)],
              'original_image_reused': True, 'runtime_admission': False, 'formal_lowering_proof': False}
    (args.output / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('CUTOVER_PREPARED')
if __name__ == '__main__': main()
