"""Bind the managed preparation receipt, engine snapshot and assembled runtime."""
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-graph'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def sources(root):
    return {str(p.relative_to(root)): sha(p) for p in (root / 'priv').rglob('*')
            if p.is_file() and p.name.endswith(('.bl', '.bl.md', '.bl.org'))}

pin = read(E / 'sdk-candidate.json')
sdk, engine = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
directory = R / '.bl/sdks' / pin['engine_fingerprint']
matches = []
for path in directory.glob('job-*/client-*/client-prepare.json'):
    envelope = read(path)
    if envelope.get('ok') is True and envelope.get('value', {}).get('output') == str(sdk):
        matches.append((path, envelope['value']))
assert len(matches) == 1
path, receipt = matches[0]
operation = path.parent.parent / 'operation.json'
request = read(operation)
assert receipt['kind'] == 'preparation-result' and receipt['operation'] == 'sdk'
assert receipt['source'] == request['source'] == str(engine)
assert receipt['operation-sha256'] == sha(operation)
baseline = read(E / 'baseline-sdk-pin.json')
predecessors = [(baseline, 'qualified-baseline')]
for candidate in E.glob('candidate-*/sdk-candidate.json'):
    predecessors.append((read(candidate), str(candidate.parent.relative_to(E))))
matched = [(item, origin) for item, origin in predecessors if item['sdk'] == request['previous']]
assert len(matched) == 1
predecessor, predecessor_origin = matched[0]
assert sha(Path(predecessor['sdk']) / 'artifact.json') == predecessor['descriptor_sha256']
assert Path(receipt['retention-root']).resolve(strict=True) == sdk
fingerprint = subprocess.check_output([R / 'scripts/sdk-inputs', '--root', engine,
                                      '--policy', R / 'nix/engine-inputs.json'], text=True).strip()
assert fingerprint == pin['engine_fingerprint']
assembly = Path(meta['source'])
engine_sources = sources(engine)
assert len(engine_sources) == 693 and engine_sources == sources(assembly)
runtime = sdk / 'lib/beam_lisp-0.1.0'
for name, digest in engine_sources.items():
    assert sha(runtime / name) == digest, name
old = read(E / 'baseline-sdk-pin.json')
old_sources = sources(Path(old['source']))
changes = {name: {'before': old_sources.get(name), 'after': engine_sources.get(name)}
           for name in sorted(old_sources.keys() | engine_sources.keys())
           if old_sources.get(name) != engine_sources.get(name)}
assert set(changes) == {'priv/lib/formal/evaluate.bl', 'priv/lib/formal/backend.bl', 'priv/lib/formal/graph-question.bl', 'priv/lib/formal/graph-execution.bl', 'priv/lib/formal/graph-terms.bl'}
oldmeta = read(Path(old['sdk']) / 'artifact.json')
unchanged = {name: meta[name] for name in ('compiler', 'dependencies', 'platform', 'formalWorker')}
assert all(oldmeta[name] == value for name, value in unchanged.items())
units = read(sdk / 'unit-store/unit-index.json')
assert all(name in units['units'] for name in ('formal.evaluate', 'formal.backend', 'formal.graph-question', 'formal.graph-execution', 'formal.graph-terms'))
(E / 'managed-operation.json').write_bytes(operation.read_bytes())
(E / 'managed-preparation-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
report = {'schema': 'enchant.formal.managed-graph-build-linkage.v1', 'sdk_pin': pin,
          'preparation_predecessor': {'sdk_pin': predecessor, 'origin': predecessor_origin,
                                      'qualified_baseline': predecessor == baseline},
          'engine_fingerprint': fingerprint, 'assembly_source': str(assembly),
          'runtime_source_sha256': engine_sources, 'source_changes': changes,
          'unchanged_components': unchanged,
          'compiled_namespace_units': {name: units['units'][name] for name in ('formal.evaluate', 'formal.backend', 'formal.graph-question', 'formal.graph-execution', 'formal.graph-terms')},
          'operation_sha256': sha(E / 'managed-operation.json'),
          'receipt_sha256': sha(E / 'managed-preparation-result.json'),
          'scope': 'Managed preparation and byte identity of all packaged BL source files; not a compiler preservation proof.'}
(E / 'build-linkage.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'bound', 'runtime_sources': len(engine_sources), 'changed_sources': list(changes)}))
