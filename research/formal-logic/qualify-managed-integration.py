"""Qualify the inventory delegate separately from core and presentation gates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
C = P / 'evidence/managed-graph'
E = P / 'evidence/managed-integration'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


core = read(C / 'qualification.json')
pin = read(C / 'sdk-candidate.json')
assert core['status'] == 'passed' and core['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
for name, digest in core['artifact_sha256'].items():
    assert sha(C / name) == digest
for name, digest in read(C / 'build-linkage.json')['runtime_source_sha256'].items():
    assert sha(R / name) == digest

delegate = 'research/formal-logic/src/formal/question-forest.bl'
expected_delegate = '''(ns formal.question-forest (:require [formal.graph-question :as sdk]))

;; Keep the existing value-key inventory and its declared profile explicit.
;; Managed requests use the separate SDK graph-key inventory profile.
(def profile sdk/profile)
(def limits sdk/limits)
(defn prepare [context] (sdk/prepare context))
'''
assert (R / delegate).read_text() == expected_delegate
original = core['stages']['paired-native-corpus']['source_pin']
comparison = read(E / 'inventory.json')
assert comparison['exact-inventories'] == len(comparison['rows']) == 187
assert len({row['id'] for row in comparison['rows']}) == 187
assert comparison['native-exchanges'] == comparison['managed-query-calls'] == 0
assert comparison['compiler-proof-authority'] is False
assert all(row['exact-values'] for row in comparison['rows'])

checks = {}
for stage in ('inventory', 'adapter', 'facade'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin and source['core_qualification_sha256'] == sha(C / 'qualification.json')
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest
        if stage == 'inventory' and name == delegate:
            assert digest == original['source_sha256'][delegate] != sha(R / name)
        else:
            assert sha(R / name) == digest, name
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired']
    command = read(E / (stage + '-command.json'))
    assert all(flag in command for flag in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group', '--cold', pin['sdk'] + '/bin/bl'))
    assert command[command.index('-p') + 1] == str(P / 'src')
    checks[stage] = {'source_pin': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}

runs = {}
for stage, files, assertions in (('adapter', 9, 4412), ('facade', 7, 585)):
    log = (E / (stage + '-checks.txt')).read_text()
    rows = {name: int(count) for name, count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
    assert len(rows) == files and sum(rows.values()) == assertions
    assert f'{files} file(s) passed, 0 failed, 0 incoherent' in log
    runs[stage] = rows

changed = subprocess.check_output(['git', 'diff', '--name-only', original['code_commit'], 'HEAD', '--',
                                   'research/formal-logic/src'], cwd=R, text=True).splitlines()
assert changed == [delegate], changed
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
report = {'schema': 'enchant.formal.managed-sdk-integration-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
          'project_pin_promoted': read(P / 'sdk-pin.json') == pin,
          'core_qualification_sha256': sha(C / 'qualification.json'), 'checks': checks, 'runs': runs,
          'assertion_executions': sum(sum(rows.values()) for rows in runs.values()),
          'exact_inventories': 187, 'inventory_sha256': sha(E / 'inventory.json'),
          'delegate': {'path': delegate, 'before_commit': original['code_commit'],
                       'before_sha256': original['source_sha256'][delegate], 'after_sha256': sha(R / delegate)},
          'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'compiler_proof_authority': False,
          'scope': 'Existing value-key project inventory delegated to its explicit compatible SDK profile after byte-exact comparison of all 187 original inventories. Focused project and language facade regressions pass on the core-qualified immutable SDK. The SDK graph-key request interface remains separately versioned. Presentation/live activation and broader totality/compiler work are separate gates.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'exact_inventories': 187, 'assertion_executions': report['assertion_executions'],
                  'project_pin_promoted': report['project_pin_promoted']}))
