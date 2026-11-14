"""Bind the wide narrative refresh to actual cells, browser and visual review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/wide-owner-presentation'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
document = P / 'ATLAS.bl.org'
for phase in ('check', 'browser'):
    q = read(E / (phase + '-qualification.json'))
    assert q['status'] == 'passed' and q['stage'] == phase
    assert q['source_pin']['sdk_pin'] == pin and q['source_pin']['document_sha256'] == sha(document)
    assert read(E / (phase + '-exit.json'))['exit_code'] == 0
    terminal = read(E / (phase + '-owner-terminal.json'))['state']
    assert terminal['SubState'] == 'exited' and terminal['MainPID'] == '0'
    assert terminal['Result'] == 'success' and terminal['ExecMainStatus'] == '0'
    for name, digest in q['source_pin']['source_sha256'].items():
        # Browser/skin/orchestration changes are not executable cell inputs.
        # Their exact active versions belong to the browser stage below.
        renderer_only = name == 'research/formal-logic/src/formal/review-host.bl'
        if phase == 'browser' or (not renderer_only and Path(name).suffix not in ('.mjs', '.css', '.py')):
            assert sha(R / name) == digest, name
assert '94 cells, 0 cell errors' in (E / 'check-checks.txt').read_text()
parent_path = P / 'evidence/obligation-presentation/dossier-qualification.json'
parent = read(parent_path)
assert parent['status'] == 'passed' and parent['sdk_pin'] == pin
browser = read(E / 'browser/audit.json')
svg = read(E / 'svg-qualification.json')
assert svg['status'] == 'passed' and svg['assertions'] == 19 and svg['private_runtime_retired'] is True
for name, digest in svg['source_pin']['source_sha256'].items():
    if name != 'research/formal-logic/src/formal/review-host.bl': assert sha(R / name) == digest
assert browser['passed'] is True and all(row['passed'] is True for row in browser['checks'])
assert len(browser['checks']) >= 35 and len(browser['screenshots']) == 36
review = read(E / 'visual-review.json')
assert review['status'] == 'reviewed' and review['document_sha256'] == sha(document)
assert len(review['frames']) == 36
assert {row['file'] for row in review['frames']} == set(browser['screenshots'])
for row in review['frames']:
    assert Path(row['file']).name == row['file']
    assert sha(E / 'browser' / row['file']) == row['sha256']
    assert isinstance(row['review'], str) and row['review'].strip()
assert {row['viewport'] for row in review['frames']} == {'phone', 'desktop'}
assert {row['theme'] for row in review['frames']} == {'day', 'night'}
chapter = document.read_text().split('* One request, more theories\n', 1)[1].split('\n* Try the language ideas', 1)[0]
declared = sorted(set(re.findall(r'\[\[file:([^\]]+)\]', chapter)))
sources = {}
for name in declared:
    path = (P / name).resolve(strict=True)
    assert path.is_relative_to(P.resolve()) and path.stat().st_size <= 8388608
    sources[name] = sha(path)
receipts = {}
for name in ['wide-owner-prototype/pure', 'wide-owner-prototype/native-smoke',
             'wide-owner-prototype/native-smoke/reader-one', 'wide-owner-prototype/native-smoke/reader-two',
             'wide-reference-reuse/identities', 'wide-reference-reuse/narrow']:
    path = P / 'evidence' / name / 'qualification.json'
    q = read(path); assert q['status'] == 'passed'
    receipts[name] = {'sha256': sha(path), 'scope': q['scope']}
installed = read(P / 'evidence/wide-integration/runtime-install.json')
assert installed['baseline_sdk_pin'] == pin and installed['sdk_produced'] is False
assert len(installed['files']) == 8
for row in installed['files']:
    assert sha(R / row['target']) == row['after'] == sha(R / row['source'])
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
own = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + own], cwd=R) == Path(__file__).read_bytes()
report = {'schema': 'bl.wide-owner-dossier-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
          'document_sha256': sha(document), 'parent_presentation_sha256': sha(parent_path),
          'check_qualification_sha256': sha(E / 'check-qualification.json'),
          'browser_qualification_sha256': sha(E / 'browser-qualification.json'),
          'cell_sources_and_results_unchanged': True, 'cells': 94,
          'browser_checks': len(browser['checks']), 'frames': 36, 'visual_review_sha256': sha(E / 'visual-review.json'),
          'renderer_marker_qualification_sha256': sha(E / 'svg-qualification.json'),
          'renderer_change_scope': 'Per-SVG marker IDs and URLs, preserved marker styling and a new presentation cache version. '
                                   'The review host is not an executable-cell dependency; browser pins bind its actual active source.',
          'chapter_sources_sha256': sources, 'source_qualifications': receipts,
          'canonical_runtime_install_sha256': sha(P / 'evidence/wide-integration/runtime-install.json'),
          'recipe': {'code_commit': commit, 'path': own, 'sha256': sha(Path(__file__))},
          'scope': 'Narrative and source-backed evidence refresh on the selected obligation SDK and frozen qualified kit. '
                   'Original 94 cell sources/results stay exact and recheck unchanged; actual browser navigation, themes, '
                   'source bytes and 36 inspected phone/desktop frames bind this presentation. The wider runtime source '
                   'is committed on main after its separate project gates. This receipt grants no new SDK, native '
                   'theory completeness, independent wide point/proof semantics or compiler authority.',
          'compiler_proof_authority': False}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'cells': 94, 'browser_checks': len(browser['checks']), 'frames': 36,
                  'sdk_changed': False, 'wide_sdk_qualification': 'separate'}))
