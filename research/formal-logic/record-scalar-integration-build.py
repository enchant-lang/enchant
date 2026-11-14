"""Bind the produced SDK to exact sources, preparation and its qualified parent."""
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/scalar-integration'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources(root):
    return {str(path.relative_to(root)): sha(path) for path in (root / 'priv').rglob('*')
            if path.is_file() and path.name.endswith(('.bl', '.bl.md', '.bl.org', '.mjs'))}

pin, baseline = read(E / 'sdk-candidate.json'), read(E / 'baseline-sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
sdk, engine = Path(pin['sdk']), Path(pin['source'])
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
metadata, old_metadata = read(sdk / 'artifact.json'), read(Path(baseline['sdk']) / 'artifact.json')
directory = R / '.bl/sdks' / pin['engine_fingerprint']
assert (directory / 'result-sdk').resolve(strict=True) == sdk
assert (directory / 'source-engine').resolve(strict=True) == engine
matches = []
for path in directory.glob('job-*/client-*/client-prepare.json'):
    envelope = read(path)
    if envelope.get('ok') is True and envelope.get('value', {}).get('output') == str(sdk):
        matches.append((path, envelope['value']))
assert len(matches) == 1
path, receipt = matches[0]
operation = path.parent.parent / 'operation.json'
request = read(operation)
assert set(request) == {'kind', 'preparation', 'previous', 'product', 'source', 'version'}
assert receipt['kind'] == 'preparation-result' and receipt['operation'] == 'sdk'
assert receipt['source'] == request['source'] == str(engine)
assert receipt['operation-sha256'] == sha(operation)
assert request['previous'] == baseline['sdk']
assert Path(receipt['retention-root']).resolve(strict=True) == sdk
fingerprint = subprocess.check_output([R / 'scripts/sdk-inputs', '--root', str(engine),
                '--policy', str(R / 'nix/engine-inputs.json')], text=True).strip()
assert fingerprint == pin['engine_fingerprint']
all_sources, old_sources = sources(engine), sources(Path(baseline['source']))
assert all_sources == sources(Path(metadata['source']))
assert sum(not name.endswith('.mjs') for name in all_sources) == 709
runtime = sdk / 'lib/beam_lisp-0.1.0'
for name, digest in all_sources.items():
    assert sha(runtime / name) == digest == sha(R / name), name
changes = {name: {'before': old_sources.get(name), 'after': all_sources.get(name)}
           for name in sorted(old_sources.keys() | all_sources.keys()) if old_sources.get(name) != all_sources.get(name)}
expected = {'priv/lib/formal/' + name + '.bl' for name in
            ['coordinates', 'evaluate', 'graph-execution', 'graph-terms', 'logic', 'point-profile',
             'request-runtime', 'finite-word-certificate', 'request-evidence', 'resources/text',
             'scalar-text-value', 'scalar-text']}
expected.add('priv/lib/oracle.bl')
assert set(changes) == expected
unchanged = {name: metadata[name] for name in ('platform', 'formalWorker')}
assert all(old_metadata[name] == value for name, value in unchanged.items())
floor_path = P / 'evidence/numeric-semantics/compiler-floor-install.json'
floor = read(floor_path)
assert floor['status'] == 'passed' and len(floor['after']) == 141
for name, digest in floor['after'].items():
    assert sha(Path(metadata['compiler']) / 'seed' / name) == digest
    assert sha(sdk / 'image/priv/bootstrap/seed' / name) == digest == sha(R / 'priv/bootstrap/seed' / name)
units = read(sdk / 'unit-store/unit-index.json')['units']
namespaces = [name.removeprefix('priv/lib/').removesuffix('.bl').replace('/', '.') for name in sorted(expected)]
for namespace in namespaces:
    unit = units[namespace]
    own = [item for item in unit['inputs'] if item['namespace'] == namespace]
    assert len(own) == 1 and own[0]['sha256'] == all_sources['priv/' + unit['file']]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
relative = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=R) == Path(__file__).read_bytes()
(E / 'managed-operation.json').write_bytes(operation.read_bytes())
(E / 'managed-preparation-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
report = {'schema': 'bl.scalar-integration-sdk-build-linkage.v1', 'status': 'bound',
          'sdk_pin': pin, 'qualified_baseline': baseline, 'engine_fingerprint': fingerprint,
          'assembly_source': metadata['source'], 'source_sha256': all_sources, 'source_changes': changes,
          'unchanged_components': unchanged, 'compiler_floor_files': 141,
          'compiler_floor_install_sha256': sha(floor_path),
          'compiled_namespace_units': {name: units[name] for name in namespaces},
          'operation_sha256': sha(E / 'managed-operation.json'), 'receipt_sha256': sha(E / 'managed-preparation-result.json'),
          'recorder': {'code_commit': commit, 'path': relative, 'sha256': sha(Path(__file__))},
          'scope': 'Exact managed preparation, packaged source bytes, thirteen compiled namespace units and unchanged qualified compiler floor/platform/native worker. Runtime gates and project selection remain separate.',
          'compiler_proof_authority': False}
(E / 'build-linkage.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'bound', 'source_files': len(all_sources), 'source_changes': len(changes),
                  'compiler_floor_files': 141, 'project_pin_changed': False}))
