"""Apply reviewed Org sources only after artifact selection; never author results."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-presentation'
C = P / 'evidence/word-integration'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
qualified = read(C / 'qualification.json')
assert qualified['status'] == 'passed' and qualified['sdk_pin'] == pin
assert read(C / 'promotion.json')['selected'] == pin
assert read(C / 'records-qualification.json')['status'] == 'passed'
assert read(C / 'records-qualification.json')['sdk_pin'] == pin
plan_path = P / 'proposals/word-dossier-plan.json'
plan = read(plan_path)
assert plan['status'] == 'proposal-awaiting-complete-sdk-qualification-and-selection'
document = P / 'ATLAS.bl.org'
assert sha(document) == plan['baseline_document_sha256']
assert (P / 'sdk-src').is_symlink() and (P / 'sdk-src').resolve() == (R / 'priv/lib').resolve()
for name in ('point-profile', 'resources/word'):
    path = P / ('sdk-src/formal/' + name + '.bl')
    assert sha(path) == sha(Path(pin['source']) / ('priv/lib/formal/' + name + '.bl'))
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
inputs = [Path(__file__), document, plan_path, P / 'proposals/word-dossier-section.org',
          P / 'proposals/word-dossier-cell.bl']
source_sha = {}
for path in inputs:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    source_sha[name] = sha(path)
before = document.read_text()
section = (P / 'proposals/word-dossier-section.org').read_text()
cell = (P / 'proposals/word-dossier-cell.bl').read_text()
assert '#+RESULTS' not in section and '#+RESULTS' not in cell
assert 'story-word-request' not in before
assert before.count('** Keep every assumption with the question\n') == 1
assert before.count('#+begin_src beam-lisp :id story-retained-request\n') == 1
assert len(re.findall(r'^#\+begin_src beam-lisp\b', before, re.M)) == 90
after = before.replace('** Keep every assumption with the question\n', section.rstrip() + '\n\n** Keep every assumption with the question\n')
after = after.replace('#+begin_src beam-lisp :id story-retained-request\n',
                      '#+begin_src beam-lisp :id story-word-request\n' + cell.rstrip() + '\n#+end_src\n\n'
                      '#+begin_src beam-lisp :id story-retained-request\n')
results = r'^#\+RESULTS:[^\n]*\n(?::[^\n]*(?:\n|$))*'
assert re.findall(results, before, re.M) == re.findall(results, after, re.M)
assert len(re.findall(r'^#\+begin_src beam-lisp\b', after, re.M)) == 91
assert after.count('#+begin_src beam-lisp :id story-word-request\n') == 1
document.write_text(after)
report = {'schema': 'bl.word-dossier-source-application.v1', 'status': 'source-applied-awaiting-real-writer',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'code_commit': commit, 'sdk_pin': pin,
          'input_source_sha256': source_sha, 'document_before_sha256': plan['baseline_document_sha256'],
          'document_after_sha256': sha(document), 'cells': 91, 'new_cell': 'story-word-request',
          'results_authored': False, 'existing_result_spans_preserved': True,
          'readable_source_projection': 'Existing sdk-src symlink to canonical priv/lib; no source copy or runtime mutation.',
          'dossier_qualified': False, 'compiler_proof_authority': False}
(E / 'dossier-source-application.json').write_text(json.dumps(report, indent=2) + '\n')
plan.update(status=report['status'], live_document_modified=True, results_authored=False,
            application_receipt='../evidence/word-presentation/dossier-source-application.json')
plan_path.write_text(json.dumps(plan, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'cells': 91, 'results_authored': False}))
