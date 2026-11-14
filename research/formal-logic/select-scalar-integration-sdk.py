"""Select only the exact fully qualified numeric-word-scalar-text SDK; no rebuilding."""
from datetime import datetime, timezone
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

pin, baseline = read(E / 'sdk-candidate.json'), read(E / 'baseline-sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
qualification = read(E / 'qualification.json')
assert qualification['status'] == 'passed' and qualification['sdk_pin'] == pin
assert qualification['baseline_sdk_pin'] == baseline and qualification['project_pin_selected'] is False
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert qualification['native_questions'] == 187 and qualification['native_outcome_differences'] == []
for name in ('records', 'previous-readers', 'prior-retained-readers', 'previous-word-readers'):
    path = E / (name + '-qualification.json')
    assert read(path)['status'] == 'passed' and read(path)['sdk_pin'] == pin
assert sha(E / 'prior-retained-readers-qualification.json') == qualification['prior_retained_qualification_sha256']
assert sha(E / 'records-qualification.json') == qualification['records_qualification_sha256']
assert sha(E / 'previous-readers-qualification.json') == qualification['previous_records_qualification_sha256']
assert sha(E / 'previous-word-readers-qualification.json') == qualification['previous_word_records_qualification_sha256']
assert sha(E / 'text-packets.json') == qualification['text_packets_sha256']
assert sha(E / 'evidence-packets.json') == qualification['evidence_packets_sha256']
linkage = read(E / 'build-linkage.json')
assert linkage['sdk_pin'] == pin and sha(E / 'build-linkage.json') == qualification['build_linkage_sha256']
for name, digest in linkage['source_sha256'].items():
    assert sha(R / name) == digest == sha(Path(pin['source']) / name)
assert subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip() == pin['engine_fingerprint']
for stage, check in qualification['stages'].items():
    for name, digest in check['source_pin']['source_sha256'].items():
        assert sha(R / name) == digest
    assert sha(E / (stage + '-command.json')) == check['command_sha256']
    assert sha(E / (stage + '-checks.txt')) == check['log_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
assert not (E / 'promotion.json').exists()
record = {'schema': 'bl.scalar-integration-sdk-promotion.v1', 'recorded_utc': datetime.now(timezone.utc).isoformat(),
          'before': baseline, 'selected': pin, 'qualification_sha256': sha(E / 'qualification.json'),
          'records_qualification_sha256': sha(E / 'records-qualification.json'),
          'previous_records_qualification_sha256': sha(E / 'previous-readers-qualification.json'),
          'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'scope': 'Project SDK selection after actual artifact gates. The preceding qualification records its preselection state. Dossier execution/browser activation follows separately; the full language goal remains active.',
          'compiler_proof_authority': False}
(E / 'selection-previous-sdk-pin.json').write_bytes((P / 'sdk-pin.json').read_bytes())
(P / 'sdk-pin.json').write_text(json.dumps(pin, indent=2) + '\n')
(E / 'promotion.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'status': 'selected', 'sdk': pin['sdk'], 'goal_complete': False, 'dossier_refresh_pending': True}))
