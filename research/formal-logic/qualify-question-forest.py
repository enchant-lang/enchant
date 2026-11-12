"""Retain original-question inventory compatibility, without execution authority."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/question-forest'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
stages = {}
for stage in ('focused', 'corpus'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest
        assert sha(R / name) == digest, (stage, name)
    result = read(E / (stage + '-exit.json'))
    assert result == {'exit_code': 0, 'runtime_retired': True}
    command = read(E / (stage + '-command.json'))
    for required in (pin['sdk'] + '/bin/bl', '--cold', '--property=MemoryMax=4G',
                     '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=900',
                     '--property=KillMode=control-group'):
        assert required in command
    stages[stage] = {'source': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
assert '65 passed' in (E / 'focused-checks.txt').read_text()
corpus = read(E / 'corpus.json')
assert len(corpus['rows']) == 187
assert corpus['managed-query-calls'] == 0 and corpus['native-execution'] == 'not-invoked'
assert corpus['compiler-proof-authority'] is False
for row in corpus['rows']:
    assert row['compiler-proof-authority'] is False
    for key in ('exact-definitions', 'ordered-roots', 'assertions', 'claim-and-counterexample',
                'observation-inventory', 'mode-and-vacuity'):
        assert row[key] is True, (row['id'], key)
report = {'schema': 'enchant.formal.question-forest-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'availability': 'project-preview',
          'sdk_pin': pin, 'stages': stages, 'focused_assertions': 65, 'questions': 187,
          'managed_query_calls': 0, 'native_execution': 'not-invoked',
          'implementation_sha256': sha(P / 'src/formal/question-forest.bl'),
          'corpus_sha256': sha(E / 'corpus.json'),
          'observation_policy': 'Original graph data and selected SDK term inventory. Uninterpreted leaves may remain unmaterialized; this is not a decoded witness.',
          'compatibility': 'Exact native definitions/root order, assertions, normalized claim/counterexample, observation term inventories, mode and vacuity on all preceding questions.',
          'scope': 'Project query preparation, not structured observation reconstruction, managed owner admission, native transport or a complete question-interpretation theorem. Existing list-observation and bare-container decoding distinctions remain explicitly under review.',
          'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'focused': 65, 'questions': 187, 'managed_queries': 0}))
