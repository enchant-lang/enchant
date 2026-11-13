"""Show actual qualification progress while preserving every existing cell/result."""
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
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
plan_path = P / 'proposals/word-dossier-plan.json'
plan = read(plan_path)
assert plan['status'] == 'proposal-awaiting-complete-sdk-qualification-and-selection'
assert read(P / 'sdk-pin.json') == read(C / 'baseline-sdk-pin.json')
checkpoint = read(C / 'assertion-checkpoint.json')
assert checkpoint['total'] == 10922 and checkpoint['status'] == 'all-three-assertion-gates-passed'
for stage in ('focused','legacy','regression'):
    result = read(C / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['complete_green_test_summary'] is True
path = P / 'ATLAS.bl.org'
assert sha(path) == plan['baseline_document_sha256']
before = path.read_text()
anchor = '** The implementation is moving\n'
assert before.count(anchor) == 1
note = '''#+begin_note :title "Word logic is in qualification"
The next build adds fixed-width words, such as eight-bit counters, to the portable request interface. It has passed 10,922 assertions, including both native word-owner checks. The complete Z3/OxiZ comparison is running. Independent saved-record checks and SDK selection follow.

The executable examples below continue to use the preceding qualified SDK. Read [[file:evidence/word-integration/assertion-checkpoint.json][the actual assertion checkpoint]] and [[file:WORD-INTEGRATION.md][the implementation status]]. The new word examples will join this page after their SDK and presentation checks pass.
#+end_note

'''
assert 'Word logic is in qualification' not in before
assert '#+RESULTS' not in note
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
relative = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+relative],cwd=R) == Path(__file__).read_bytes()
after = before.replace(anchor,anchor+note)
for pattern in [r'^#\+begin_src beam-lisp\b[^\n]*\n.*?^#\+end_src[^\n]*',
                r'^#\+RESULTS:[^\n]*\n(?::[^\n]*(?:\n|$))*',
                r'^#\+name:[^\n]*\n(?:\|[^\n]*(?:\n|$))*']:
    assert re.findall(pattern,before,re.M|re.S) == re.findall(pattern,after,re.M|re.S)
assert len(re.findall(r'^#\+begin_src beam-lisp\b',after,re.M)) == 90
old_sha = sha(path)
path.write_text(after)
plan['baseline_document_sha256'] = sha(path)
plan['prequalification_progress_document_sha256'] = sha(path)
plan['prequalification_progress_note'] = 'Actual completed assertion gates; existing executable sources and result spans remain unchanged on the preceding SDK.'
plan_path.write_text(json.dumps(plan,indent=2)+'\n')
report = {'schema':'bl.word-dossier-progress-source.v1','status':'progress-source-updated-awaiting-complete-word-presentation-loop',
          'recorded_utc':datetime.now(timezone.utc).isoformat(),'document_before_sha256':old_sha,'document_sha256':sha(path),
          'sdk_pin_for_existing_examples':read(P / 'sdk-pin.json'),'candidate_sdk_pin':read(C / 'sdk-candidate.json'),
          'assertion_checkpoint_sha256':sha(C / 'assertion-checkpoint.json'),'actual_assertions':10922,
          'existing_cell_and_result_spans_unchanged':True,'cells':90,'results_authored':False,
          'presentation_requalification':'pending the selected word SDK writer, independent check and actual browser review',
          'recipe':{'code_commit':commit,'path':relative,'sha256':sha(Path(__file__))},'compiler_proof_authority':False}
(E / 'progress-source-application.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'cells_unchanged':90,'results_authored':False}))
