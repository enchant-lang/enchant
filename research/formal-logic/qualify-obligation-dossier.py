"""Actual obligation and premise cell/browser evidence; no proof authority promotion."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/obligation-presentation'
C = P / 'evidence/obligation-integration'
I = P / 'evidence/managed-integration'
O = P / 'evidence/observation-semantics'
K = E / 'kit-state.json'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
assert read(C / 'qualification.json')['status'] == 'passed'
assert read(C / 'qualification.json')['sdk_pin'] == pin
assert read(I / 'qualification.json')['status'] == 'passed'
parent = read(P / 'evidence/scalar-integration/qualification.json')
assert parent['status'] == 'passed' and parent['sdk_pin'] == read(C / 'qualification.json')['baseline_sdk_pin']
assert read(C / 'promotion.json')['selected'] == pin
assert read(C / 'previous-scalar-readers-qualification.json')['status'] == 'passed'
assert read(C / 'previous-scalar-readers-qualification.json')['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
kit = read(K)
assert str(Path(kit['snapshot_retention_root']).resolve(strict=True)) == kit['root']
assert subprocess.check_output(['nix-store', '--query', '--hash', kit['root']], text=True).strip() == kit['snapshot_nar_hash']
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest
document = P / 'ATLAS.bl.org'
text = document.read_text()
assert len(re.findall(r'^#\+begin_src beam-lisp\b', text, re.M)) == 94
assert re.findall(r'^#\+begin_src beam-lisp\b[^\n]*:id ([^\s]+)[^\n]*:frozen\b', text, re.M) == ['story-float-backends']
recorded = read(O / 'recorded-float-native.json')
assert recorded['sdk_pin'] == read(P / 'evidence/shared-primitives/baseline-sdk-pin.json')
assert recorded['sdk_pin'] != pin and recorded['execution']['exit_code'] == 0
assert sha(Path(recorded['sdk_pin']['sdk']) / 'artifact.json') == recorded['sdk_pin']['descriptor_sha256']
captured = subprocess.check_output(['git', 'show', recorded['result_commit'] + ':research/formal-logic/ATLAS.bl.org'], cwd=R)
assert hashlib.sha256(captured).hexdigest() == recorded['execution']['document_sha256']
retained = re.search(r'^#\+begin_src beam-lisp :id story-float-backends :frozen\n(.*?)^#\+end_src\n#\+RESULTS: story-float-backends\n(:[^\n]*\n)', text, re.M | re.S)
assert retained and retained.group(1) == recorded['source'] and retained.group(2) == recorded['result_span']
assert hashlib.sha256(retained.group(1).encode()).hexdigest() == recorded['source_sha256']
assert hashlib.sha256(retained.group(2).encode()).hexdigest() == recorded['result_sha256']
checks = {}
for stage in ('dossier-inputs', 'dossier-cells', 'dossier-check', 'focused-browser', 'full-browser'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin and source['kit_state_sha256'] == sha(K)
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest
        if name.endswith('/ATLAS.bl.org') and stage in ('dossier-inputs', 'dossier-cells'):
            for pattern in (r'^#\+begin_src beam-lisp\b[^\n]*\n.*?^#\+end_src[^\n]*',
                            r'^#\+name:[^\n]*\n(?:\|[^\n]*(?:\n|$))*'):
                assert re.findall(pattern, body.decode(), re.M | re.S) == re.findall(pattern, text, re.M | re.S)
        elif (stage.startswith('dossier-') or stage == 'full-browser') and name in (
                'research/formal-logic/obligation-browser.mjs', 'research/formal-logic/run-obligation-presentation.py'):
            # Preserve the real writer/check launch version above. These two
            # scripts do not execute inside a cell or the independent full
            # audit. The focused audit must match their current source exactly.
            pass
        elif stage.startswith('dossier-') and name in ('research/formal-logic/story-audit.mjs',
                'research/formal-logic/src/formal/review-host.bl'):
            # The browser audit is not a cell dependency. Its actual current
            # source is required by both fresh browser stage pins below.
            pass
        else:
            assert sha(R / name) == digest, name
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired']
    command = read(E / (stage + '-command.json'))
    cap = '2G' if stage.endswith('browser') else '4G'
    ceiling = ('300' if stage == 'focused-browser' else '900') if stage.endswith('browser') else '1200'
    assert all(flag in command for flag in ('--property=MemoryMax=' + cap, '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + ceiling, '--property=KillMode=control-group'))
    log = (E / (stage + '-checks.txt')).read_text()
    if stage.startswith('dossier-'):
        imports = [str(P / 'src'), str(P / 'dossier'), str(Path(kit['root']) / 'bl-org-dossier/kit'),
                   str(Path(kit['root']) / 'codebase-review/kit'),
               str(Path(kit['root']) / 'research-elements/kit')]
        assert 'BEAM_LISP_PATH=' + ':'.join(imports) in command and pin['sdk'] + '/bin/bl' in command and '--cold' in command
        if stage == 'dossier-inputs':
            assert ':notebook :valid' in log and ':native-query-calls 0' in log
        else:
            assert '94 cells, 0 cell errors' + (' (checked, unchanged)' if stage == 'dossier-check' else '') in log
    if stage in ('dossier-check', 'focused-browser', 'full-browser'):
        assert result['document_sha256'] == source['document_sha256'] == sha(document)
    checks[stage] = {'source_pin': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')), 'log_sha256': sha(E / (stage + '-checks.txt'))}
audits = {}
for stage in ('focused-browser', 'full-browser'):
    audit = read(E / stage / 'audit.json')
    assert audit['passed'] and all(row['passed'] for row in audit['checks'])
    audits[stage] = audit
assert len(audits['focused-browser']['checks']) >= 190 and len(audits['full-browser']['checks']) >= 1601
visual = read(E / 'focused-browser/visual-review.json')
assert visual['status'] == 'reviewed' and len(visual['inspected']) >= 4
assert any('phone' in name for name in visual['inspected']) and any('desktop' in name for name in visual['inspected'])
assert any('night' in name for name in visual['inspected'])
for name in visual['inspected']:
    assert name in audits['focused-browser']['screenshots'] and sha(E / 'focused-browser' / name) == visual['sha256'][name]
tools = read(E / 'browser-tools.json')
for name, tool in tools.items():
    assert str((R / ('.bl/formal-dossier-' + name)).resolve(strict=True)) == tool['package']
    assert subprocess.check_output(['nix-store', '--query', '--hash', tool['package']], text=True).strip() == tool['nar_hash']
host = read(E / 'dossier-host.json')
assert host['document_sha256'] == sha(document) and host['sdk_boot'] == pin['sdk'] + '/boot.exs' and host['kit_root'] == kit['root']
assert host['state']['ActiveState'] == 'active' and host['state']['MemoryMax'] == '2147483648'
assert all(response['status'] == 200 and response['bytes'] > 1000000 for response in host['responses'].values())
# Project host and local styles remain unchanged. The current immutable kit
# snapshot and its actual source hashes are checked separately above.
old = read(O / 'full-browser-source-pin.json')['source_sha256']
activation = read(E / 'host-launch-source-pin.json')
assert activation['sdk_pin'] == pin and activation['kit_state_sha256'] == sha(K)
assert activation['document_sha256'] == sha(document)
for name, digest in activation['source_sha256'].items():
    assert sha(R / name) == digest
    assert hashlib.sha256(subprocess.check_output(['git', 'show', activation['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest
assert read(E / 'host-launch-exit.json')['exit_code'] == 0
styles = {}
for name in ('research/formal-logic/dossier-local.css', 'research/formal-logic/presentation.css',
             'research/formal-logic/review-serve.bl'):
    current = sha(R / name)
    if name != 'research/formal-logic/dossier-local.css':
        assert current == old[name]
    else:
        change = read(E / 'before-mobile-evidence-cards/style-change.json')
        assert change['before_sha256'] == old[name] and change['after_sha256'] == current
    styles[name] = {'baseline_sha256': old[name], 'current_sha256': current}
research = read(E / 'research/qualification.json')
assert research['status'] == 'passed' and research['sdk_pin'] == pin
assert research['assertions'] == 38 and research['browser_save_qualified'] is False
for name, digest in research['source_sha256'].items():
    assert sha(R / name) == digest
snapshot_path = P / 'elements/word-answer-evidence.bl.org'
snapshot_capture = read(E / 'research/capture-exit.json')
assert snapshot_capture['exit_code'] == 0 and snapshot_capture['runtime_retired'] and snapshot_capture['cwd_retired']
assert snapshot_capture['snapshot_sha256'] == sha(snapshot_path) and snapshot_capture['prior_bytes_preserved']
assert snapshot_capture['prior_snapshot_sha256'] == read(P / 'evidence/scalar-presentation/research/capture-exit.json')['snapshot_sha256']
assert len(re.findall(r'^#\+begin_research_element\b', snapshot_path.read_text(), re.M)) == 3
assert len(re.findall(r'^#\+begin_research_element\b', text, re.M)) == 1
probe = read(E / 'research-browser/audit.json')
probe_exit = read(E / 'research-browser/exit.json')
assert probe['passed'] and all(row['passed'] for row in probe['checks'])
assert probe['snapshot']['revisions'] == 5 and probe['snapshot']['source_fixture_restored']
assert probe_exit['exit_code'] == 0 and probe_exit['runtime_retired'] and probe_exit['fixture_retired'] and probe_exit['host_stopped']
probe_source = read(E / 'research-browser/source-pin.json')
assert probe_source['sdk_pin'] == pin and probe_source['kit_state_sha256'] == sha(K)
for name, digest in probe_source['source_sha256'].items():
    assert sha(R / name) == digest
    assert hashlib.sha256(subprocess.check_output(['git', 'show', probe_source['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest
probe_visual = read(E / 'research-browser/visual-review.json')
assert probe_visual['status'] == 'reviewed' and len(probe_visual['inspected']) >= 4
for name in probe_visual['inspected']:
    assert name in probe['screenshots'] and sha(E / 'research-browser' / name) == probe_visual['sha256'][name]
report = {'schema': 'bl.obligation-dossier-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
          'implementation_qualification_sha256': sha(C / 'qualification.json'),
          'parent_scalar_qualification_sha256': sha(P / 'evidence/scalar-integration/qualification.json'),
          'inherited_numeric_qualification_sha256': sha(P / 'evidence/numeric-semantics/qualification.json'),
          'inherited_integration_qualification_sha256': sha(I / 'qualification.json'),
          'previous_records_qualification_sha256': sha(C / 'previous-scalar-readers-qualification.json'),
          'floor_modulus_model_qualification_sha256': sha(P / 'evidence/floor-modulus-model/qualification.json'),
          'document_sha256': sha(document), 'cells': {'total': 94, 'fresh_live': 93, 'recorded_native': 1},
          'recorded_native_sha256': sha(O / 'recorded-float-native.json'),
          'recorded_native_sdk_pin': recorded['sdk_pin'], 'checks': checks,
          'research_evidence': {'checks': 38, 'snapshot_sha256': sha(snapshot_path),
                                'browser_checks': len(probe['checks']), 'actual_snapshot_revisions': 5,
                                'browser_audit_sha256': sha(E / 'research-browser/audit.json'), 'visual_review': probe_visual},
          'host': host, 'kit_state_sha256': sha(K), 'rendering_sources': styles,
          'browser': {'focused_checks': len(audits['focused-browser']['checks']),
                      'full_checks': len(audits['full-browser']['checks']), 'visual_review': visual,
                      'focused_audit_sha256': sha(E / 'focused-browser/audit.json'),
                      'full_audit_sha256': sha(E / 'full-browser/audit.json'), 'tools': tools},
          'scope': 'Actual nine-case proof/premise/acceptance grid on the qualified obligation SDK, with all prior source-backed comparison revisions retained. Integer choice and Source examples retain their project-prototype and reviewed implementation boundaries. Actual bounded scalar text and word requests, explicit native text capability differences, solver-free eight-value conditional certificates, fresh proof packet checking and caller-budget refusal. Actual bounded word requests and retained requests on both native backends, caller-only versus complete point meanings, expired unused callbacks and independently reopened point evidence. Numeric relations and the measured source-backed chart remain checked. The complete document is executed and unchanged, with one exact historical Float observation, current immutable kit/live SDK identity and inspected phone/desktop frames. Native history stays recorded; mathematical models and implementation correspondence remain separate. Wider managed theory profiles, compiler preservation and language totality remain open.',
          'rendering_source_route_changes': [read(E / path / 'renderer-change.json') for path in
             ['before-declared-element-source-route-fix', 'before-immutable-sdk-source-route-fix']],
          'compiler_proof_authority': False}
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
report['recipe'] = {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'live_cells': 93, 'full_checks': report['browser']['full_checks'],
                  'focused_checks': report['browser']['focused_checks']}))
