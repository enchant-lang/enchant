"""Bind the focused selection-model presentation to code, model and full audit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/graph-selection-model'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


snapshot = read(E / 'dossier-source-pin.json')
document = P / 'ATLAS.bl.org'
assert sha(document) == snapshot['document_sha256']
for name, digest in snapshot['source_sha256'].items():
    assert sha(R / name) == digest, name
    assert hashlib.sha256(subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest
baseline_path = P / 'evidence/graph-consumers/dossier-qualification.json'
baseline = read(baseline_path)
assert baseline['sdk_pin'] == snapshot['sdk_pin'] == read(P / 'sdk-pin.json')
for name, digest in baseline['host_sources']['source_sha256'].items():
    assert sha(R / name) == digest, 'unchanged qualified host: ' + name
old = subprocess.check_output(['git', 'show', baseline['document']['cell_results_commit'] + ':' + str(document.relative_to(R))], cwd=R, text=True)
new = document.read_text()


def cells(text):
    source = re.findall(r'^#\+begin_src beam-lisp[^\n]*\n[\s\S]*?^#\+end_src[^\n]*', text, re.M)
    lines = text.splitlines()
    results = []
    for i, line in enumerate(lines):
        if line.startswith('#+RESULTS:'):
            body = []
            for value in lines[i + 1:]:
                if not value.startswith(':'):
                    break
                body.append(value)
            results.append((line, body))
    return source, results


old_cells, new_cells = cells(old), cells(new)
assert old_cells == new_cells and len(new_cells[0]) == len(new_cells[1]) == 80
assert '80 cells, 0 cell errors (checked, unchanged)' in (E / 'dossier-checks.txt').read_text()
model = read(E / 'qualification.json')
model_pin = read(P / 'metatheory/graph-selection-pin.json')
assert model['status'] == 'passed' and (model['general_theorems'], model['example_theorems'], model['negative_controls']) == (7, 5, 4)
assert sha(E / 'qualification.json') == model_pin['qualification']['sha256']
for name, digest in model['source_pin']['source_sha256'].items():
    assert sha(R / name) == digest
for item in ('source', 'compiled'):
    assert sha(P / model_pin[item]['path']) == model_pin[item]['sha256']
audit = read(E / 'browser-audit/audit.json')
assert audit['passed'] and all(row['passed'] for row in audit['checks'])
manual = ['phone-selection-proof.png', 'phone-selection-proof-details.png', 'phone-selection-meaning.png',
          'desktop-selection-proof.png', 'desktop-selection-proof-night.png', 'desktop-selection-meaning.png']
visual = read(E / 'browser-audit/visual-review.json')
assert visual['status'] == 'reviewed' and visual['inspected'] == manual
assert set(manual) == set(audit['screenshots'])
host = read(E / 'dossier-host.json')
assert host['same_service_as_full_audit'] and host['document_sha256'] == sha(document)
assert host['http']['status'] == 200 and host['http']['selection_counts_present'] and host['http']['bytes'] > 1000000
assert host['state']['ExecMainPID'] == baseline['host']['state']['ExecMainPID']
report = {'schema': 'enchant.formal.graph-selection-dossier-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': snapshot['sdk_pin'],
          'source_pin': snapshot, 'document': {'sha256': sha(document), 'executable_cells': 80,
          'source_and_stored_results_unchanged_from_full_audit': True, 'fresh_cell_check_sha256': sha(E / 'dossier-checks.txt')},
          'preceding_full_dossier_qualification_sha256': sha(baseline_path),
          'model_qualification_sha256': sha(E / 'qualification.json'), 'host': host,
          'browser': {'checks': len(audit['checks']), 'audit_sha256': sha(E / 'browser-audit/audit.json'),
          'screenshots': {name: sha(E / 'browser-audit' / name) for name in manual}, 'visual_review': visual},
          'scope': 'Focused proof-panel, copy, source-link and unchanged-cell update on the same host. The preceding full receipt retains wider graph/role/media checks. Conditional mathematical value agreement is not BL reachability, admission, typed-term or compiler preservation.',
          'compiler_proof_authority': False}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'cells': 80, 'focused_browser_checks': len(audit['checks']), 'manually_reviewed_frames': len(manual)}))
