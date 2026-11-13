"""Bind the exact numeric SDK to its real preparation and complete sources."""
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources(root):
    return {str(path.relative_to(root)): sha(path) for path in (root / 'priv').rglob('*')
            if path.is_file() and path.name.endswith(('.bl', '.bl.md', '.bl.org', '.mjs'))}

pin = read(E / 'sdk-candidate.json')
baseline = read(E / 'baseline/sdk-pin.json')
sdk, engine = Path(pin['sdk']), Path(pin['source'])
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
metadata = read(sdk / 'artifact.json')
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
assert receipt['kind'] == 'preparation-result' and receipt['operation'] == 'sdk'
assert receipt['source'] == request['source'] == str(engine)
assert receipt['operation-sha256'] == sha(operation)
assert Path(receipt['retention-root']).resolve(strict=True) == sdk
known = [(baseline, 'qualified-baseline', True)]
for archived in E.glob('candidate-*/sdk-candidate.json'):
    previous = read(archived)
    failure = read(archived.parent / 'failure.json')
    assert failure['status'] == 'unqualified' and failure['sdk_pin'] == previous
    known.append((previous, str(archived.parent.relative_to(E)), False))
previous = [item for item in known if item[0]['sdk'] == request['previous']]
assert len(previous) == 1
predecessor, origin, qualified = previous[0]
assert sha(Path(predecessor['sdk']) / 'artifact.json') == predecessor['descriptor_sha256']
fingerprint = subprocess.check_output([R / 'scripts/sdk-inputs', '--root', str(engine),
                '--policy', str(R / 'nix/engine-inputs.json')], text=True).strip()
assert fingerprint == pin['engine_fingerprint']
all_sources = sources(engine)
assert all_sources == sources(Path(metadata['source']))
assert sum(not name.endswith('.mjs') for name in all_sources) == 700
runtime = sdk / 'lib/beam_lisp-0.1.0'
for name, digest in all_sources.items():
    assert sha(runtime / name) == digest == sha(R / name), name
old_sources = sources(Path(baseline['source']))
changes = {name: {'before': old_sources.get(name), 'after': all_sources.get(name)}
           for name in sorted(old_sources.keys() | all_sources.keys()) if old_sources.get(name) != all_sources.get(name)}
assert set(changes) == {'priv/boot/rt.bl', 'priv/host/decimal.bl', 'priv/host/num.bl',
    'priv/lib/decimal.bl', 'priv/lib/system/smt.bl', 'priv/lib/js/rt.mjs',
    'priv/lib/js/host-leaves.mjs', 'priv/lib/js/leaves.mjs'}
old_metadata = read(Path(baseline['sdk']) / 'artifact.json')
unchanged = {name: metadata[name] for name in ('platform', 'formalWorker')}
assert all(old_metadata[name] == value for name, value in unchanged.items())
floor = read(E / 'compiler-floor-install.json')
assert floor['status'] == 'passed'
for name, digest in floor['after'].items():
    assert sha(Path(metadata['compiler']) / 'seed' / name) == digest
    assert sha(sdk / 'image/priv/bootstrap/seed' / name) == digest == sha(R / 'priv/bootstrap/seed' / name)
assert len(floor['after']) == 141
units = read(sdk / 'unit-store/unit-index.json')
assert 'decimal' in units['units'] and 'system.smt' in units['units']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
relative = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=R) == Path(__file__).read_bytes()
(E / 'managed-operation.json').write_bytes(operation.read_bytes())
(E / 'managed-preparation-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
report = {'schema': 'bl.numeric-sdk-build-linkage.v1', 'status': 'bound', 'sdk_pin': pin,
          'qualified_baseline': baseline, 'preparation_predecessor': {'sdk_pin': predecessor,
              'origin': origin, 'qualified': qualified},
          'engine_fingerprint': fingerprint, 'assembly_source': metadata['source'],
          'source_sha256': all_sources, 'source_changes': changes,
          'unchanged_components': unchanged, 'compiler_floor_files': 141,
          'compiler_floor_install_sha256': sha(E / 'compiler-floor-install.json'),
          'compiler_components': {name: {'before': old_metadata[name], 'after': metadata[name]}
                                  for name in ('compiler', 'dependencies')},
          'compiled_namespace_units': {name: units['units'][name] for name in ('decimal', 'system.smt')},
          'operation_sha256': sha(E / 'managed-operation.json'),
          'receipt_sha256': sha(E / 'managed-preparation-result.json'),
          'recorder': {'code_commit': commit, 'source': relative, 'sha256': sha(Path(__file__))},
          'scope': 'Managed preparation, exact packaged BL/JS sources and complete compiler-floor byte identity. Gate results and project selection remain separate.',
          'compiler_proof_authority': False}
(E / 'build-linkage.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'bound', 'source_files': len(all_sources), 'changes': list(changes),
                  'compiler_floor_files': 141, 'qualified_predecessor': qualified}))
