"""Record primitive forecast controls and bounded growth probes, not totality."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/observation-semantics'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
assert pin == read(E / 'sdk-candidate.json') == read(E / 'qualification.json')['sdk_pin']
assert read(E / 'qualification.json')['status'] == 'passed'
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
stages = {}
for stage in ('integer-preflight', 'value-growth'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        original = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(original).hexdigest() == digest
        if name != 'research/formal-logic/run-observation-semantics.py':
            assert sha(R / name) == digest
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired']
    command = read(E / (stage + '-command.json'))
    assert all(item in command for item in (pin['sdk'] + '/bin/bl', '--cold',
               '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group'))
    stages[stage] = {'source_pin': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
log = (E / 'integer-preflight-checks.txt').read_text()
assert 'formal.integer-preflight-test  10248 passed' in log
assert '1 file(s) passed, 0 failed, 0 incoherent' in log
growth = read(E / 'value-growth.json')
assert growth['managed-query-calls'] == 0 and growth['compiler-proof-authority'] is False
assert len(growth['rows']) == 3
expected = {'integer': (16, 17, 65537, 'integer-bits'), 'text': (16, 17, 65536, 'utf8-bytes'),
            'sequence': (12, 14, 4096, 'elements')}
assert {row['kind'] for row in growth['rows']} == set(expected)
for row in growth['rows']:
    assert (row['layers'], row['typed-nodes'], row['derived-size'], row['unit']) == expected[row['kind']]
    assert row['evaluated-nodes'] == row['typed-nodes']
    assert row['resource-preflight'] == 'not-implemented' and row['compiler-proof-authority'] is False
report = {'schema': 'enchant.formal.integer-preflight-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
          'availability': 'standalone-project-planner', 'focused_assertions': 10248, 'stages': stages,
          'planner_sha256': sha(P / 'src/formal/integer-preflight.bl'),
          'growth_probe_sha256': sha(E / 'value-growth.json'), 'growth': growth,
          'primitive_execution_by_planner': 'not-run', 'managed_query_calls_by_planner': 0,
          'scope': 'Integer primitive size forecasts compared with finite signed SDK evaluations and sparse large operands, plus three small actual unmetered growth probes. Planner reports do not authorize execution. No cumulative accounting, other-value-family policy, evaluator/owner integration, universal cost correspondence or totality theorem is established.',
          'compiler_proof_authority': False}
(E / 'integer-preflight-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'focused_assertions': 10248, 'growth_fixtures': 3,
                  'evaluator_integration': 'not-implemented'}))
