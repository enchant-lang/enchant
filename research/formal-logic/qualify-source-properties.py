"""Qualify source-derived term questions, actual ANF replay and their exact SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/source-properties'

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def require(ok, reason):
    if not ok:
        raise AssertionError(reason)

def counts(p):
    return {name: int(n) for name, n in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', p.read_text())}

pin, snapshot = read(P / 'sdk-pin.json'), read(E / 'sdk-source-pin.json')
require(pin == snapshot['sdk_pin'], 'selected immutable SDK')
sdk, source = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'] and meta['source'] == str(source), 'SDK descriptor and source')
for name, digest in snapshot['source_sha256'].items():
    require(sha(R / name) == digest, 'unchanged implementation: ' + name)
    require(hashlib.sha256(subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest,
            'committed implementation: ' + name)
    if name.startswith('priv/'):
        require(sha(source / name) == digest, 'actual SDK source: ' + name)
for name, digest in read(E / 'check-source-pin.json')['source_sha256'].items():
    require(sha(R / name) == digest, 'actual checked program: ' + name)
prior = read(E / 'baseline-sdk-pin.json')
previous = read(Path(prior['sdk']) / 'artifact.json')
require(meta['compiler'] == previous['compiler'] and meta['formalWorker'] == previous['formalWorker'], 'same qualified compiler and native worker')
for path in (R / 'priv/lib/formal').glob('*.bl'):
    old = Path(prior['source']) / path.relative_to(R)
    if old.exists() and path.name != 'source.bl':
        require(sha(path) == sha(old), 'unchanged preceding formal module: ' + path.name)
build, floor, preflight = (read(E / n) for n in ('managed-build-result.json', 'produced-compiler.json', 'source-preflight.json'))
require(build['status'] == 'succeeded' and build['exit_code'] == 0 and build['spawn_count'] == 1, 'managed SDK production')
require(floor['status'] == 'passed' and floor['sdk'] == pin['sdk'] and floor['files'] == 141, 'complete qualified compiler floor')
require(preflight['beam-selection']['modality'] == 'proven' and not any(preflight[k] for k in
        ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')), 'Source preflight')
require('0 passed, 5 failed' in (E / 'baseline-checks.txt').read_text(), 'five actual preceding SDK failures')
require('not green' in (E / 'focused-1-checks.txt').read_text(), 'retained first candidate replay failures')
focused = counts(E / 'focused-checks.txt')
require(len(focused) == 5 and focused.get('veritas.source-terms-test', 0) > 400
        and '5 file(s) passed, 0 failed, 0 incoherent' in (E / 'focused-checks.txt').read_text(), 'focused source and sampling checks')
regression = counts(E / 'regression-checks.txt')
require(len(regression) == 26 and sum(regression.values()) > 7086
        and '26 file(s) passed, 0 failed, 0 incoherent' in (E / 'regression-checks.txt').read_text(), 'formal regression and promoted source adapters')
paired = 0
for name in ('advanced', 'features', 'native'):
    now = read(E / 'regression' / (name + '.json'))
    old = {x['id']: x for x in read(P / 'evidence/temporal/regression' / (name + '.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'paired matrix healthy')
    require(old.keys() == {x['id'] for x in now['cases']}, 'same paired matrix questions')
    for row in now['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete question')
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')), 'same native capability')
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'actual matrix SDK')
    paired += len(now['cases'])
require(paired == 187, '187 paired questions')
for name in ('focused-command.json', 'regression-command.json', 'examples-command.json'):
    command = read(E / name)
    require(str(sdk / 'bin/bl') in command, 'exact selected SDK command')
    for var in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH'):
        require(any(command[i:i+2] == ['-u', var] for i in range(len(command)-1)), 'default SDK artifact selection')
example = read(E / 'examples.json')
require(example['research-import-path'] is False and not Path(example['cwd']).is_relative_to(R)
        and '-p' not in read(E / 'examples-command.json'), 'ordinary SDK-only use from unrelated cwd')
rows = example['native']
require([r['backend'] for r in rows] == ['z3', 'oxiz'], 'both backends')
for row in rows:
    require(row['law'] == 'solver-claim' and row['native-certificate'] == 'not-checked', 'honest native claim')
    require(row['failure'] == 'refuted' and row['witness'] == -2 and row['result'] == 0
            and row['term-replay'] == 'valid' and row['runtime-replay'] == 'reproduced', 'real counterexample')
    require(row['crash-status'] == 'raised' and row['crash-phase'] == 'invocation'
            and row['crash-replay'] == 'reproduced' and row['modules-loaded'] == [False, False, False], 'actual invocation crash and code retirement')
    require(row['empty-domain'] == 'vacuous', 'empty domain')
for field in ('law-question', 'failure-question'):
    require(rows[0][field] == rows[1][field], 'same source-derived question')
require(rows[0]['guarded-division']['question'] == rows[1]['guarded-division']['question']
        and [r['guarded-division']['modality'] for r in rows] == ['solver-claim', 'unknown'], 'recorded guarded division capability difference')
require(example['term-proof']['status'] == 'checked' and example['term-proof']['verdict'] == 'entails'
        and example['term-proof']['source-connection'] == 'reviewed', 'checked term proof and reviewed source connection')
report = {'schema': 'enchant.formal.source-properties-qualification.v1', 'checkpoint': 35, 'sdk_pin': pin,
          'source': {'code_commit': snapshot['code_commit'], 'sha256': snapshot['source_sha256']},
          'managed_build': {'id': build['id'], 'status': build['status']},
          'focused': focused, 'regression': regression, 'bl_assertions': sum(focused.values()) + sum(regression.values()),
          'paired_questions': paired, 'sdk_only': True, 'counterexample_basis': ['independent-term-replay', 'same-anf-invocation'],
          'replay_code_retired': True, 'term_certificate': 'checked', 'source_connection': 'reviewed',
          'guarded_division': {'z3': 'solver-claim', 'oxiz': 'unknown'}, 'compiler_proof_authority': False,
          'evidence_sha256': {n: sha(E/n) for n in ('focused-checks.txt', 'regression-checks.txt', 'examples.json',
                              'managed-build-result.json', 'produced-compiler.json', 'source-preflight.json')}}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'checkpoint': 35, 'assertions': report['bl_assertions'], 'paired_questions': paired}))
