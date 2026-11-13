"""Bind scalar resource checks to committed sources and the qualified SDK."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/bounded-point'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
qualified = read(P / 'evidence/observation-semantics/qualification.json')
assert qualified['status'] == 'passed' and qualified['sdk_pin'] == pin
stages = {}
for stage in ('focused', 'example'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest == sha(R / name), name
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired']
    command = read(E / (stage + '-command.json'))
    assert all(flag in command for flag in (pin['sdk'] + '/bin/bl', '--cold',
               '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group'))
    stages[stage] = {'source_pin': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
counts = {'bounded-point': 345, 'term-forest-evaluate': 107, 'term-forest': 521,
          'graph-reader': 24, 'graph-observations': 102, 'question-forest': 71}
log = (E / 'focused-checks.txt').read_text()
for name, count in counts.items():
    assert f'formal.{name}-test  {count} passed' in log
assert '6 file(s) passed, 0 failed, 0 incoherent' in log
example = read(E / 'example.json')
bounded = example['result']['bounded']
assert bounded['profile'] == 'bl/bounded-bool-int-point-preview-v1' and bounded['status'] == 'incomplete'
assert bounded['resources']['integer-primitive-calls'] == 4
assert bounded['resources']['charged-work-units'] == 119
assert len(bounded['resources']['refusals']) == 1
assert bounded['resources']['refusals'][0]['reason'] == {
    'kind': 'resource-limit', 'metric': 'integer-bits', 'required': 34, 'limit': 32}
assert bounded['checking']['typed-nodes'] == 17 and len(bounded['source-roots']) == 2
assert bounded['values'][0] == bounded['values'][1]
for name in ('bounded', 'decided', 'complete'):
    result = example['result'][name]
    assert result['native-calls'] == 0 and result['assertion-replay'] == 'not-run'
    assert result['compiler-proof-authority'] is False
    assert all(result[key]['sha256'] for key in ('data-reference', 'assignment-reference', 'settings-reference', 'evaluation-reference'))
assert example['result']['decided']['values'] == [False] and example['result']['decided']['status'] == 'complete'
assert len(example['result']['decided']['resources']['refusals']) == 1
assert example['result']['complete']['values'] == [63] and example['result']['complete']['status'] == 'complete'
report = {'schema': 'enchant.formal.bounded-point-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
          'profile': bounded['profile'], 'availability': 'project-preview',
          'focused_assertions': sum(counts.values()), 'assertions_by_file': counts, 'stages': stages,
          'example_sha256': sha(E / 'example.json'), 'managed_query_calls': 0,
          'compiler_proof_authority': False,
          'scope': 'Fresh original Bool/Int graph admission, private integer preflight/reservation and cumulative request accounting, shared-node memoization, demand-compatible incompleteness, exact graph/assignment/settings/root-order identities, process/lifetime refusal and SDK semantic compatibility. Other value families, ordinary SDK entry-point budgets, managed assertion replay and implementation/cost-model or compiler preservation remain open.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'focused_assertions': sum(counts.values())}))
