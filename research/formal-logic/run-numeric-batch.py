"""Durable serial qualification gates on one fixed numeric SDK candidate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'
pin = json.loads((E / 'sdk-candidate.json').read_text())
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for source in (Path(__file__), P / 'run-numeric-checks.py', P / 'run-numeric-semantics.py'):
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    sources[name] = hashlib.sha256(source.read_bytes()).hexdigest()
completed = []
stages = ['compiler-floor', 'preflight', 'preflight-controls', 'observations',
          'js-unit', 'focused', 'datom', 'managed', 'regression', 'native']
start = 0
if len(sys.argv) > 1:
    assert len(sys.argv) == 3 and sys.argv[1] == '--from'
    start = stages.index(sys.argv[2])
    # Reuse completed checks of this exact artifact. Final qualification still
    # audits their actual inputs, commands, logs and historical source commits.
    for stage in stages[:start]:
        if stage == 'observations':
            summary = json.loads((E / 'candidate/observation-summary.json').read_text())
            assert summary['sdk_pin'] == pin
            assert summary['differences'] == {'beam': 0, 'js-direct': 0, 'js-compiled': 0}
            for part in ('beam', 'js-direct', 'js-build', 'js-compiled'):
                assert json.loads((E / 'candidate' / (part + '-exit.json')).read_text())['exit_code'] == 0
        else:
            assert json.loads((E / (stage + '-source-pin.json')).read_text())['sdk_pin'] == pin
            assert json.loads((E / (stage + '-exit.json')).read_text())['exit_code'] == 0
        completed.append(stage)
for stage in stages[start:]:
    assert json.loads((E / 'sdk-candidate.json').read_text()) == pin
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in sources.items())
    command = ([sys.executable, str(P / 'run-numeric-semantics.py'), 'candidate', str(E / 'sdk-candidate.json')]
               if stage == 'observations' else [sys.executable, str(P / 'run-numeric-checks.py'), stage])
    state = {'schema': 'bl.numeric-sdk-check-batch.v1', 'status': 'running', 'stage': stage,
             'completed': completed, 'sdk_pin': pin, 'code_commit': commit, 'source_sha256': sources,
             'recorded_utc': datetime.now(timezone.utc).isoformat(), 'command': command,
             'reused_prefix': stages[:start],
             'project_pin_selected': False, 'compiler_proof_authority': False}
    (E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run(command, cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='checks-completed', completed=completed, exit_code=0,
             next='Audit exact source/artifact bindings and all results before selecting this SDK.')
(E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': 'checks-completed', 'stages': completed, 'project_pin_selected': False}), flush=True)
