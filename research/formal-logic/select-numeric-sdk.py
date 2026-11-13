"""Select only an audited numeric SDK; preserve the preceding qualified pin."""
from datetime import datetime, timezone
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


report = read(E / 'qualification.json')
pin = read(E / 'sdk-candidate.json')
before = read(P / 'sdk-pin.json')
assert report['status'] == 'passed' and report['sdk_pin'] == pin
assert before == report['baseline_sdk_pin'] and before != pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert sha(E / 'build-linkage.json') == report['build_linkage_sha256']
for name, digest in read(E / 'build-linkage.json')['source_sha256'].items():
    assert sha(R / name) == sha(Path(pin['source']) / name) == digest
assert sha(E / 'candidate/observation-summary.json') == report['observation_summary_sha256']
observations = read(E / 'candidate/observation-summary.json')
for name, digest in observations['reports_sha256'].items():
    assert sha(E / 'candidate' / (name + '.json')) == digest
assert sha(E / 'candidate/compiled-manifest.json') == observations['compiled_manifest_sha256']
assert sha(E / 'candidate/compiled.tar.gz') == observations['compiled_archive_sha256']
assert sha(E / 'native.json') == report['native_sha256']
for stage, gate in report['stages'].items():
    assert read(E / (stage + '-exit.json')) == gate['exit']
    assert sha(E / (stage + '-command.json')) == gate['command_sha256']
    assert sha(E / (stage + '-checks.txt')) == gate['log_sha256']
    for name, digest in gate['source_pin']['source_sha256'].items():
        if name != 'research/formal-logic/run-numeric-checks.py':
            assert sha(R / name) == digest, name
model = read(P / 'evidence/floor-modulus-model/qualification.json')
assert model['status'] == 'passed' and model['universal_and_example_theorems'] == 10
for name, digest in model['source_pin']['source_sha256'].items():
    assert sha(R / name) == digest
for check in model['checks']:
    assert sha(R / check['source']) == check['source_sha256']
    directory = P / 'evidence/floor-modulus-model'
    stem = Path(check['source']).stem
    assert sha(directory / (stem + '-checks.txt')) == check['log_sha256']
    if check['accepted']:
        assert sha(directory / (stem + '.olean')) == check['olean_sha256']
compatibility = read(E / 'previous-readers-qualification.json')
assert compatibility['status'] == 'passed' and compatibility['sdk_pin'] == pin
assert compatibility['recorded_producer_sdk_pin'] == before
assert compatibility['native_exchanges'] == compatibility['managed_query_calls'] == 0
for name, digest in compatibility['artifact_sha256'].items():
    assert sha(E / 'previous-readers' / name) == digest
for name, digest in compatibility['source_pin']['source_sha256'].items():
    assert sha(R / name) == digest
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
assert not (E / 'promotion.json').exists(), 'Do not overwrite a recorded selection.'
promotion = {'schema': 'bl.numeric-sdk-selection.v1', 'status': 'selected',
             'recorded_utc': datetime.now(timezone.utc).isoformat(), 'previous_sdk_pin': before,
             'sdk_pin': pin, 'qualification_sha256': sha(E / 'qualification.json'),
             'mathematical_model_qualification_sha256': sha(P / 'evidence/floor-modulus-model/qualification.json'),
             'previous_records_qualification_sha256': sha(E / 'previous-readers-qualification.json'),
             'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
             'presentation_refresh': 'pending-actual-cell-execution-and-browser-qualification',
             'compiler_proof_authority': False}
(E / 'selection-previous-sdk-pin.json').write_text(json.dumps(before, indent=2) + '\n')
(P / 'sdk-pin.json').write_text(json.dumps(pin, indent=2) + '\n')
(E / 'promotion.json').write_text(json.dumps(promotion, indent=2) + '\n')
print(json.dumps({'status': 'selected', 'sdk': pin['sdk'], 'presentation_refresh': 'pending', 'compiler_proof_authority': False}))
