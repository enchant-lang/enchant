"""Qualify checked query connections and declared size arithmetic on one SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/query-preparation'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, reason):
    if not ok:
        raise AssertionError(reason)


def counts(name, files):
    text = (E / name).read_text()
    rows = {n: int(v) for n, v in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    require(len(rows) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in text,
            'complete successful run: ' + name)
    return rows


pin = read(E / 'sdk-candidate.json')
sdk, source = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'] and meta['source'] == str(source), 'immutable SDK descriptor and source')
previous = read(Path(read(E / 'baseline-sdk-pin.json')['sdk']) / 'artifact.json')
require(meta['compiler'] == previous['compiler'] and meta['formalWorker'] == previous['formalWorker'], 'unchanged compiler and native engines')
production = read(E / 'preparation-result.json')
require(production['ok'] is True and production['value']['operation'] == 'sdk'
        and production['value']['output'] == pin['sdk'], 'managed immutable preparation')
snapshot = read(E / 'sdk-source-pin.json')
require(snapshot['sdk_pin'] == pin and len(snapshot['source_sha256']) == 41, 'complete relevant library source pin')
for name, digest in snapshot['source_sha256'].items():
    require(sha(R / name) == sha(source / name) == digest, 'exact SDK implementation: ' + name)
    committed = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)
    require(hashlib.sha256(committed).hexdigest() == digest, 'committed implementation: ' + name)
checked = read(E / 'check-source-pin.json')
for name, digest in checked['source_sha256'].items():
    require(sha(R / name) == digest, 'checked program: ' + name)
    committed = subprocess.check_output(['git', 'show', checked['code_commit'] + ':' + name], cwd=R)
    require(hashlib.sha256(committed).hexdigest() == digest, 'committed checked program: ' + name)
units = read(sdk / 'unit-store/unit-index.json')['units']
require(all(n in units for n in ('formal.preparation', 'formal.affine', 'formal.integer-optimize', 'system.linear'))
        and 'formal.optimize' not in units, 'native SDK interfaces and namespace separation')
focused = counts('focused-checks.txt', 5)
preceding = counts('preceding-focused-checks.txt', 26)
regression = counts('regression-checks.txt', 31)
require(regression['veritas.model-serve-test'] >= 59, 'owned admission control and rejected-body checks')
require(focused['system.formal-preparation-test'] >= 109 and focused['system.linear-terms-test'] >= 126
        and focused['system.linear-term-baseline-test'] == 8 and focused['system.linear-test'] >= 36,
        'fresh connection, model boundary, constructive arithmetic and actual emission checks')
require(focused['system.linear-verdict-baseline-test'] == 7, 'unknown truth and independent search budgets')
require('1 passed, 6 failed' in (E / 'verdict-baseline-checks.txt').read_text(), 'retained verdict and budget baseline')
require('0 passed, 8 failed' in (P / 'evidence/compiler-linearity/baseline-checks.txt').read_text(), 'retained legacy interface baseline')
require('95 passed, 4 failed' in (E / 'focused-1-checks.txt').read_text(), 'retained first candidate model-boundary review')
http_failure = (E / 'regression-before-http-isolation/regression-checks.txt').read_text()
require('refused request admission log' in http_failure and ':method :head' in http_failure,
        'retained unrelated HTTP request in preceding admission assertion')
isolation = read(E / 'regression-runtime.json')
require(isolation['retired'] is True and not Path(isolation['path']).exists()
        and '--setenv=XDG_RUNTIME_DIR=' + isolation['path'] in read(E / 'regression-command.json'),
        'private test runtime retired after the complete run')
require(preceding['veritas.answer-binding-baseline-test'] == 10
        and preceding['veritas.ledger-large-terms-test'] >= 21, 'preceding reply and durable payload boundaries')

paired = 0
for name in ('advanced', 'features', 'native'):
    now = read(E / 'regression' / (name + '.json'))
    old = {x['id']: x for x in read(P / 'evidence/answer-binding/regression' / (name + '.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'healthy native matrix: ' + name)
    require(old.keys() == {x['id'] for x in now['cases']}, 'same preceding questions')
    for row in now['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete question: ' + row['id'])
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')), 'same preceding native capability')
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'native matrix provenance')
    paired += len(now['cases'])
require(paired == 187, '187 preceding paired questions')

for name in ('focused', 'preceding-focused', 'regression', 'examples', 'ledger-write', 'ledger-read'):
    command = read(E / (name + '-command.json'))
    require(str(sdk / 'bin/bl') in command, 'exact SDK command: ' + name)
    require(all(any(command[i:i+2] == ['-u', var] for i in range(len(command)-1))
                for var in ('BEAM_LISP_PATH', 'ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY')), 'default native artifact selection')
example = read(E / 'examples.json')
require(example['research-import-path'] is False and not Path(example['cwd']).is_relative_to(R)
        and '-p' not in read(E / 'examples-command.json'), 'SDK-only unrelated-directory consumer')
cases = example['cases']
require([(x['backend'], x['placement']) for x in cases] == [('z3', 1), ('z3', 2), ('oxiz', 1), ('oxiz', 2)], 'paired declared size cases')
families = example['size-families']
require(families['checked']['status'] == 'checked' and families['checked']['holds'] is True,
        'positive family has checked evidence')
require(families['unknown']['status'] == 'unknown' and families['unknown']['holds'] is None
        and families['unknown']['arities'][0]['linear']['native']['result']['verdict'] == 'proved',
        'theorem budget abstains despite a separate unchecked native positive label')
require(families['refuted']['status'] == 'refuted' and families['refuted']['holds'] is False
        and families['refuted']['arities'][0]['linear']['counterexample']['checking']['status'] == 'checked-data-connection',
        'false needs a checked single-placement counterexample')
for row in cases:
    plan, original, result = row['plan'], row['original-answer'], row['prepared-answer']
    require(plan['formal/preparation'] == 1 and plan['status'] == 'ready'
            and plan['checking']['status'] == result['preparation']['status'] == 'checked', 'fresh checked question connection')
    require(plan['original'] == original['question'] == result['question']
            and plan['execution'] == result['execution']['question'] == result['execution']['answer']['question'], 'complete original and executed bindings')
    require(all(x['status'] == 'checked' for x in result['preparation']['rows']), 'every actual question site checked')
    require(result['verdict'] == ('proved' if row['placement'] == 1 else 'refuted') and result['phase'] == 'query', 'prepared native answer')
    require(result['certificate']['status'] == 'not-checked' and result['compiler-proof-authority'] is False, 'equivalence never becomes native theorem authority')
    require(result['backend']['name'] == row['backend'] and result['identity']['artifacts']['sdk'] == pin['sdk'], 'actual backend and SDK provenance')
    require(result['model-status-basis'] == 'executed-question', 'native API access retains its execution basis')
    if row['placement'] == 1:
        require(row['portable-proof']['status'] == row['portable-proof']['checking']['status'] == 'checked', 'separate positive portable object')
        require(result['original-replay']['status'] == 'not-applicable', 'absence answer has no original model replay')
    else:
        require(result['validation']['status'] == result['original-replay']['status'] == 'valid', 'original assertion and observation replay')
    if row['backend'] == 'oxiz':
        require(original['verdict'] == 'unknown', 'retained exact original OxiZ uncertainty')
for placement in (1, 2):
    same = [x for x in cases if x['placement'] == placement]
    require(same[0]['question'] == same[1]['question'] and same[0]['execution-question'] == same[1]['execution-question']
            and same[0]['plan'] == same[1]['plan'], 'both engines receive the same complete plan')

write, reread = (read(E / n) for n in ('ledger-write.json', 'ledger-read.json'))
require(write['mode'] == 'write' and reread['mode'] == 'read' and write['process'] != reread['process'], 'separate durable processes')
require(write['rows'] == reread['rows'] == 4 and write['claims'] == reread['claims'], 'complete durable claims')
require(all(x['managed-query-calls'] == 0 and x['managed-query-scope'] == 'record-rechecking'
            and x['fresh-connections'] == 'checked' and x['original-replay'] == 'reproduced'
            and x['compiler-proof-authority'] is False for x in (write, reread)), 'fresh pure record checking window')
floor, preflight = (read(E / n) for n in ('produced-compiler.json', 'source-preflight.json'))
require(floor['status'] == 'passed' and floor['files'] == 141 and floor['sdk'] == pin['sdk'], 'produced compiler floor')
require(preflight['root'] == str(source) and preflight['runtime'] == str(sdk), 'actual immutable source preflight')
require(all(preflight[k]['modality'] == 'exhausted' and preflight[k]['complete'] is True for k in ('beam-selection', 'declaration-cases'))
        and not any(preflight[k] for k in ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')), 'complete healthy source analysis')
require('SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text(), 'source refusal controls')
total = sum(sum(x.values()) for x in (focused, preceding, regression))
report = {'schema': 'enchant.formal.query-preparation-qualification.v1', 'checkpoint': 39,
          'sdk_pin': pin, 'source': snapshot, 'bl_assertions': total,
          'checks': {'focused': focused, 'preceding': preceding, 'regression': regression,
                     'focused_assertions': sum(focused.values()), 'preceding_assertions': sum(preceding.values()),
                     'regression_assertions': sum(regression.values())},
          'unchanged_paired_questions': paired, 'sdk_only': True, 'durable_ledger_fresh_process': True,
          'normalizer': 'untrusted producer with fresh per-plan unconditional equality certificates',
          'original_models': 'separate assertion replay, binding availability and observation availability',
          'compiler_scope': 'declared size recurrence, conditional connection to actual compiler',
          'compiler_proof_authority': False,
          'evidence_sha256': {n: sha(E / n) for n in ('focused-checks.txt', 'preceding-focused-checks.txt',
             'regression-checks.txt', 'examples.json', 'ledger-write.json', 'ledger-read.json',
             'produced-compiler.json', 'source-preflight.json')}}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'checkpoint': 39, 'assertions': total, 'paired_questions': paired}))
