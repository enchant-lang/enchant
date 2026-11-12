"""Qualify the live project preview separately from code and mathematical proofs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/question-forest'
C = P / 'evidence/term-forest-evaluation'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


source = read(E / 'dossier-source-pin.json')
pin = read(P / 'sdk-pin.json')
assert source['sdk_pin'] == pin and source['document_sha256'] == sha(P / 'ATLAS.bl.org')
for name, digest in source['source_sha256'].items():
    assert sha(R / name) == digest
    assert hashlib.sha256(subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest
text = (P / 'ATLAS.bl.org').read_text()
assert len(re.findall(r'^#\+begin_src beam-lisp\b', text, re.M)) == 83
assert '83 cells, 0 cell errors' in (C / 'dossier-cells-checks.txt').read_text()
assert '83 cells, 0 cell errors (checked, unchanged)' in (C / 'dossier-checks.txt').read_text()
assert read(C / 'dossier-check-exit.json')['exit_code'] == 0
retained = read(C / 'dossier-qualification.json')
assert retained['status'] == 'passed' and retained['sdk_pin'] == pin
assert retained['document']['cells'] == 83
assert retained['document']['run_log_sha256'] == sha(C / 'dossier-cells-checks.txt')
assert retained['document']['unchanged_check_log_sha256'] == sha(C / 'dossier-checks.txt')
for name, digest in retained['source_pin']['source_sha256'].items():
    if name != 'research/formal-logic/ATLAS.bl.org':
        assert sha(R / name) == digest, 'retained executable dependency changed: ' + name
# This update changes presentation blocks and links only. Retain the exact committed
# checked state and compare every executable span/result rather than rerunning
# all native examples for presentation-only content. This is an after-check committed
# source anchor, not a claim that a launch-time snapshot existed.
checked_commit = '7bd5a85484ff264e68416f3ab71c1ff0bff18cef'
checked_text = subprocess.check_output(['git', 'show', checked_commit + ':research/formal-logic/ATLAS.bl.org'], cwd=R).decode()
patterns = [r'^#\+begin_src beam-lisp\b[^\n]*\n.*?^#\+end_src[^\n]*',
            r'^#\+RESULTS:[^\n]*\n(?::[^\n]*(?:\n|$))*']
for pattern in patterns:
    assert re.findall(pattern, checked_text, re.M | re.S) == re.findall(pattern, text, re.M | re.S)
implementation = read(E / 'qualification.json')
assert implementation['status'] == 'passed' and implementation['sdk_pin'] == pin
assert implementation['implementation_sha256'] == sha(P / 'src/formal/question-forest.bl')
assert implementation['availability'] == 'project-preview' and implementation['questions'] == 187 and implementation['focused_assertions'] == 68
baseline = read(P / 'evidence/graph-consumers/dossier-qualification.json')
for name, digest in baseline['host_sources']['source_sha256'].items():
    if name == 'research/formal-logic/browser-driver.mjs':
        continue  # Test helper is qualified by the new full/focused source pins.
    assert sha(R / name) == digest
kit = read(P / 'evidence/graph-consumers/kit-state.json')
assert source['kit_state_sha256'] == sha(P / 'evidence/graph-consumers/kit-state.json')
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest
full = read(E / 'full-browser/audit.json')
full_source = read(E / 'full-browser-source-pin.json')
assert full_source['document_sha256'] == sha(P / 'ATLAS.bl.org')
assert full_source['source_sha256']['research/formal-logic/story-audit.mjs'] == sha(P / 'story-audit.mjs')
focused = read(E / 'focused-browser/audit.json')
for audit in (full, focused):
    assert audit['passed'] and all(row['passed'] for row in audit['checks'])
graphs = sorted({row['name'].split('/')[1].split(':')[0] for row in full['checks'] if row['name'].endswith(': connected topic opens')})
assert len(graphs) == 49 and 'formal-graph-consumers' in graphs
manual = ['phone-question-inventory-chapter.png', 'phone-question-inventory.png', 'phone-question-inventory-details.png', 'desktop-question-inventory-chapter.png', 'desktop-question-inventory.png', 'desktop-question-inventory-night.png']
visual = read(E / 'focused-browser/visual-review.json')
assert visual['status'] == 'reviewed' and visual['inspected'] == manual
assert set(manual) == set(focused['screenshots'])
host = read(E / 'dossier-host.json')
assert host['same_service_as_preceding_full_audit'] and host['state']['ExecMainPID'] == baseline['host']['state']['ExecMainPID']
assert host['document_sha256'] == sha(P / 'ATLAS.bl.org') and host['http']['status'] == 200 and host['http']['bytes'] > 1000000
report = {'schema': 'enchant.formal.question-forest-dossier-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'source_pin': source,
          'implementation_qualification_sha256': sha(E / 'qualification.json'), 'host': host,
          'retained_execution_qualification_sha256': sha(C / 'dossier-qualification.json'),
          'document': {'sha256': sha(P / 'ATLAS.bl.org'), 'cells': 83,
          'cell_check_commit': checked_commit,
          'cell_check_document_sha256': hashlib.sha256(checked_text.encode()).hexdigest(),
          'cell_check_scope': 'All executable spans and stored results identical to the committed fresh 83-cell check. This update changes presentation prose, graph topics and source links only.',
          'run_log_sha256': sha(C / 'dossier-cells-checks.txt'), 'unchanged_check_log_sha256': sha(C / 'dossier-checks.txt')},
          'browser': {'full_checks': len(full['checks']), 'focused_checks': len(focused['checks']),
          'full_input_source_pin': full_source,
          'review_graphs': graphs, 'full_audit_sha256': sha(E / 'full-browser/audit.json'),
          'focused_audit_sha256': sha(E / 'focused-browser/audit.json'), 'visual_review': visual,
          'screenshots': {name: sha(E / 'focused-browser' / name) for name in manual}},
          'scope': 'Retained 83 executed cells; fresh whole-dossier browser interactions and focused whole-question inventory discussion/source review. The new inventory behavior has separate 68-assertion and 187-question code qualification; this presentation adds no executed inventory cell, managed admission, witness reconstruction or compiler authority.',
          'compiler_proof_authority': False}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'cells': 83, 'full_browser_checks': len(full['checks']), 'focused_browser_checks': len(focused['checks']), 'manual_frames': len(manual)}))
