"""Keep actual dossier execution/browser evidence separate from logic authority."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/observation-semantics'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def original(snapshot, name):
    body = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)
    assert hashlib.sha256(body).hexdigest() == snapshot['source_sha256'][name]
    return body

pin = read(P / 'sdk-pin.json')
qualification = read(E / 'qualification.json')
assert qualification['status'] == 'passed' and qualification['sdk_pin'] == pin
kit = read(E / 'kit-state.json')
for name, digest in kit['rendering_source_sha256'].items():
    body = (Path(kit['root']) / name).read_bytes()
    assert hashlib.sha256(body).hexdigest() == digest
    assert subprocess.check_output(['git', 'show', kit['commit'] + ':' + name], cwd=kit.get('repository_root', kit['root'])) == body
document = P / 'ATLAS.bl.org'
text = document.read_text()
assert len(re.findall(r'^#\+begin_src beam-lisp\b', text, re.M)) == 84
identities = re.findall(r'^#\+begin_src beam-lisp\b[^\n]*:id ([^\s]+)', text, re.M)
assert len(identities) == len(set(identities))
checks = {}
for stage in ('inputs', 'cells', 'check'):
    prefix = 'dossier-' + stage
    snapshot = read(E / (prefix + '-source-pin.json'))
    assert snapshot['sdk_pin'] == pin and snapshot['kit_state_sha256'] == sha(E / 'kit-state.json')
    for name, digest in snapshot['source_sha256'].items():
        body = original(snapshot, name)
        if name == 'research/formal-logic/ATLAS.bl.org':
            # A writer changes stored results; subsequent prose can change too.
            # Every executable span, its order/attributes, and every model table
            # must stay identical to the actual launch-time document.
            for pattern in (r'^#\+begin_src beam-lisp\b[^\n]*\n.*?^#\+end_src[^\n]*',
                            r'^#\+name:[^\n]*\n(?:\|[^\n]*(?:\n|$))*'):
                assert re.findall(pattern, body.decode(), re.M | re.S) == re.findall(pattern, text, re.M | re.S)
            if stage == 'check':
                pattern = r'^#\+RESULTS:[^\n]*\n(?::[^\n]*(?:\n|$))*'
                assert re.findall(pattern, body.decode(), re.M | re.S) == re.findall(pattern, text, re.M | re.S)
        else:
            assert sha(R / name) == digest
    result = read(E / (prefix + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired']
    command = read(E / (prefix + '-command.json'))
    imports = [str(P / 'src'), str(Path(kit['root']) / 'bl-org-dossier/kit'),
               str(Path(kit['root']) / 'codebase-review/kit')]
    assert snapshot['project_import_paths'] == imports
    assert 'BEAM_LISP_PATH=' + ':'.join(imports) in command
    assert str(Path(pin['sdk']) / 'bin/bl') in command and '--cold' in command
    assert all(item in command for item in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
                                            '--property=RuntimeMaxSec=1200', '--property=KillMode=control-group'))
    log = (E / (prefix + '-checks.txt')).read_text()
    if stage == 'inputs':
        assert ':notebook :valid' in log and ':project-imports :loaded' in log and ':native-query-calls 0' in log
    else:
        expected = '84 cells, 0 cell errors' + (' (checked, unchanged)' if stage == 'check' else '')
        assert expected in log
    if stage == 'check':
        assert result['document_sha256'] == snapshot['source_sha256']['research/formal-logic/ATLAS.bl.org']
    checks[stage] = {'source_pin': snapshot, 'exit': result, 'log_sha256': sha(E / (prefix + '-checks.txt'))}

snapshot = read(E / 'dossier-source-pin.json')
assert snapshot['sdk_pin'] == pin and snapshot['document_sha256'] == sha(document)
assert snapshot['kit_state_sha256'] == sha(E / 'kit-state.json')
for name, digest in snapshot['source_sha256'].items():
    original(snapshot, name)
    assert sha(R / name) == digest
full_pin = read(E / 'full-browser-source-pin.json')
assert full_pin['document_sha256'] == sha(document) and full_pin['sdk_pin'] == pin
assert full_pin['kit_state_sha256'] == sha(E / 'kit-state.json')
for name, digest in full_pin['source_sha256'].items():
    original(full_pin, name)
    if name not in ('research/formal-logic/observation-browser.mjs', 'research/formal-logic/run-observation-browser.py'):
        assert sha(R / name) == digest
audits = {}
for stage in ('focused', 'full'):
    assert read(E / (stage + '-browser-exit.json'))['exit_code'] == 0
    audit = read(E / (stage + '-browser/audit.json'))
    assert audit['passed'] and all(row['passed'] for row in audit['checks'])
    audits[stage] = audit
assert len(audits['full']['checks']) >= 1599 and len(audits['focused']['checks']) >= 40
graphs = sorted({r['name'].split('/')[1].split(':')[0] for r in audits['full']['checks']
                 if r['name'].endswith(': connected topic opens')})
assert len(graphs) == 49 and 'formal-graph-consumers' in graphs
visual = read(E / 'focused-browser/visual-review.json')
assert visual['status'] == 'reviewed' and len(visual['inspected']) >= 6
assert all(name in audits['focused']['screenshots'] for name in visual['inspected'])
assert any('phone' in name for name in visual['inspected']) and any('desktop' in name for name in visual['inspected'])
assert any('night' in name for name in visual['inspected'])
host = read(E / 'dossier-host.json')
assert host['document_sha256'] == sha(document) and host['live_process_sdk_boot'] == pin['sdk'] + '/boot.exs'
assert host['state']['ActiveState'] == 'active' and host['state']['MemoryMax'] == '2147483648'
assert host['http']['status'] == 200 and host['http']['bytes'] > 1000000
assert host['kit_commit'] == kit['commit']
tailnet = read(E / 'tailnet.json')
assert tailnet['status'] == 200 and tailnet['document_sha256'] == sha(document)
report = {'schema': 'enchant.formal.observation-dossier-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
          'source_pin': snapshot, 'implementation_qualification_sha256': sha(E / 'qualification.json'),
          'host': host, 'tailnet': tailnet, 'document': {'sha256': sha(document), 'cells': 84, 'execution': checks},
          'kit_state_sha256': sha(E / 'kit-state.json'), 'kit_commit': kit['commit'],
          'browser': {'full_checks': len(audits['full']['checks']), 'focused_checks': len(audits['focused']['checks']),
                      'full_source_pin': full_pin, 'review_graphs': graphs,
                      'full_audit_sha256': sha(E / 'full-browser/audit.json'),
                      'focused_audit_sha256': sha(E / 'focused-browser/audit.json'), 'visual_review': visual,
                      'inspected_frame_sha256': {name: sha(E / 'focused-browser' / name) for name in visual['inspected']}},
          'scope': 'Fresh executed dossier cells, upgraded committed kit, actual host and browser/source interactions. Code compatibility and native outcomes have separate qualification. No complete evaluator/decoder/implementation or compiler proof is granted.',
          'compiler_proof_authority': False}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'cells': 84, 'full_checks': len(audits['full']['checks']),
                  'focused_checks': len(audits['focused']['checks']), 'inspected_frames': len(visual['inspected'])}))
