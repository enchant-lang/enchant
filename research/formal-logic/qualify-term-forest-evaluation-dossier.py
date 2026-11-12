"""Qualify the live project preview separately from code and mathematical proofs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/term-forest-evaluation'


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
assert '83 cells, 0 cell errors' in (E / 'dossier-cells-checks.txt').read_text()
assert '83 cells, 0 cell errors (checked, unchanged)' in (E / 'dossier-checks.txt').read_text()
assert read(E / 'dossier-check-exit.json')['exit_code'] == 0
implementation = read(E / 'qualification.json')
assert implementation['status'] == 'passed' and implementation['sdk_pin'] == pin
assert implementation['stages']['focused']['source']['source_sha256']['research/formal-logic/src/formal/term-forest-evaluate.bl'] == sha(P / 'src/formal/term-forest-evaluate.bl')
assert implementation['availability'] == 'project-preview' and implementation['exact_root_comparisons'] == 6300 and implementation['point_maps'] == 748
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
manual = ['phone-sharing-default.png', 'phone-sharing-adjusted.png', 'phone-sharing-formula.png', 'phone-graph-point.png', 'phone-graph-point-cell.png', 'desktop-sharing-default.png', 'desktop-sharing-adjusted.png', 'desktop-sharing-formula.png', 'desktop-graph-point.png', 'desktop-graph-point-night.png', 'desktop-graph-point-cell.png']
visual = read(E / 'focused-browser/visual-review.json')
assert visual['status'] == 'reviewed' and visual['inspected'] == manual
assert set(manual) == set(focused['screenshots'])
host = read(E / 'dossier-host.json')
assert host['same_service_as_preceding_full_audit'] and host['state']['ExecMainPID'] == baseline['host']['state']['ExecMainPID']
assert host['document_sha256'] == sha(P / 'ATLAS.bl.org') and host['http']['status'] == 200 and host['http']['bytes'] > 1000000
report = {'schema': 'enchant.formal.term-forest-evaluation-dossier-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'source_pin': source,
          'implementation_qualification_sha256': sha(E / 'qualification.json'), 'host': host,
          'document': {'sha256': sha(P / 'ATLAS.bl.org'), 'cells': 83,
          'run_log_sha256': sha(E / 'dossier-cells-checks.txt'), 'unchanged_check_log_sha256': sha(E / 'dossier-checks.txt')},
          'browser': {'full_checks': len(full['checks']), 'focused_checks': len(focused['checks']),
          'full_input_source_pin': full_source,
          'review_graphs': graphs, 'full_audit_sha256': sha(E / 'full-browser/audit.json'),
          'focused_audit_sha256': sha(E / 'focused-browser/audit.json'), 'visual_review': visual,
          'screenshots': {name: sha(E / 'focused-browser' / name) for name in manual}},
          'scope': 'Executed graph evaluator and all 17 notebook settings, full existing kit interactions, real pointer adjustment and nested formula/source inspection. Illustrative counts do not claim more evaluator executions. No managed query promotion, independent solver certificate, evaluator-equivalence theorem or compiler authority is inferred.',
          'compiler_proof_authority': False}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'cells': 83, 'full_browser_checks': len(full['checks']), 'focused_browser_checks': len(focused['checks']), 'manual_frames': len(manual)}))
