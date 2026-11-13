"""Qualify explicit-profile project delegates against the immutable SDK."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/shared-primitives'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
core = read(E / 'qualification.json')
assert core['status'] == 'passed' and core['sdk_pin'] == pin == read(E / 'sdk-candidate.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert core['assertion_executions'] == 14167 and core['native_differences'] == []
for name, digest in core['artifact_sha256'].items():
    assert sha(E / name) == digest, name
for name, digest in read(E / 'build-linkage.json')['runtime_source_sha256'].items():
    assert sha(R / name) == digest, name

stage = 'adapter-integration'
source = read(E / (stage + '-source-pin.json'))
assert source['sdk_pin'] == pin
for name, digest in source['source_sha256'].items():
    body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
    assert hashlib.sha256(body).hexdigest() == digest == sha(R / name), name
result = read(E / (stage + '-exit.json'))
assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired']
command = read(E / (stage + '-command.json'))
assert all(flag in command for flag in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=900', '--property=KillMode=control-group', '--cold', pin['sdk'] + '/bin/bl'))
log = (E / (stage + '-checks.txt')).read_text()
runs = {name: int(count) for name, count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
assert len(runs) == 9 and sum(runs.values()) == 4412
assert '9 file(s) passed, 0 failed, 0 incoherent' in log
old_source = core['stages']['paired-native-corpus']['source_pin']
changed = subprocess.check_output(['git', 'diff', '--name-only', old_source['code_commit'], 'HEAD', '--',
                                   'research/formal-logic/src'], cwd=R, text=True).splitlines()
expected = ['research/formal-logic/src/formal/' + name + '.bl' for name in (
    'integer-preflight', 'rational-preflight', 'term-forest', 'term-forest-evaluate')]
assert set(changed) == set(expected), changed
adapters = {}
for name in expected:
    old = subprocess.check_output(['git', 'show', old_source['code_commit'] + ':' + name], cwd=R)
    assert hashlib.sha256(old).hexdigest() == old_source['source_sha256'][name]
    adapters[name] = {'before_commit': old_source['code_commit'], 'before_sha256': hashlib.sha256(old).hexdigest(),
                      'before_lines': len(old.splitlines()), 'after_sha256': sha(R / name),
                      'after_lines': len((R / name).read_text().splitlines())}
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
report = {'schema': 'enchant.formal.shared-sdk-integration-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'project_pin_promoted': True,
          'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'core_qualification_sha256': sha(E / 'qualification.json'),
          'integration_source_pin': source, 'integration_exit': result,
          'command_sha256': sha(E / (stage + '-command.json')), 'log_sha256': sha(E / (stage + '-checks.txt')),
          'runs': runs, 'assertion_executions': 4412, 'adapters': adapters,
          'compiler_proof_authority': False,
          'scope': 'The project selects the exact qualified SDK. Four project prototypes now delegate to SDK admission, resource and evaluator interfaces. Earlier API names explicitly select their earlier policy profiles; targeted project consumer, privacy/lifetime, phase, semantic and trace assertions pass. The SDK core/native qualification remains its own historical source snapshot. Live dossier execution/host/browser qualification is a separate gate. No new managed replay, totality or compiler preservation is established.'}
(E / 'integration-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'assertion_executions': 4412,
                  'project_lines_removed': sum(row['before_lines'] - row['after_lines'] for row in adapters.values())}))
