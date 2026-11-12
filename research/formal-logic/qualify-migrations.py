"""Qualify closed migration claims, source replay and durable pure rechecking."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/migrations'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(ok, why):
    if not ok:
        raise AssertionError(why)

def counts(stage, files):
    text = (E / (stage + '-checks.txt')).read_text()
    rows = {name: int(value) for name, value in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    require(len(rows) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in text, 'complete run: ' + stage)
    return rows

pin = read(E / 'sdk-candidate.json')
sdk, source = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'] and meta['source'] == pin['source'], 'immutable SDK source')
prior = read(Path(read(E / 'baseline-sdk-pin.json')['sdk']) / 'artifact.json')
require(meta['compiler'] == prior['compiler'] and meta['formalWorker'] == prior['formalWorker'], 'same compiler and native worker')
production = read(E / 'preparation-result.json')
require(production['ok'] and production['value']['operation'] == 'sdk' and production['value']['output'] == pin['sdk'], 'managed SDK production')
snapshot = read(E / 'sdk-source-pin.json')
require(snapshot['sdk_pin'] == pin and len(snapshot['source_sha256']) == 43, 'all relevant SDK sources')
for name, digest in snapshot['source_sha256'].items():
    require(sha(R / name) == sha(source / name) == digest, 'exact SDK source: ' + name)
    require(hashlib.sha256(subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest,
            'committed source: ' + name)
checked = read(E / 'check-source-pin.json')
for name, digest in checked['source_sha256'].items():
    require(sha(R / name) == digest, 'unchanged checked program: ' + name)
    require(hashlib.sha256(subprocess.check_output(['git', 'show', checked['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest,
            'committed checked program: ' + name)
units = read(sdk / 'unit-store/unit-index.json')['units']
require('formal.migration' in units and 'formal.integer-optimize' in units and 'formal.optimize' not in units, 'SDK interfaces')
require('103 passed, 2 errored' in (E / 'candidate-1/focused-checks.txt').read_text(), 'retained closed-admission failure')
require(':closed-within true' in (E / 'candidate-1/domain-checks.txt').read_text(), 'observed composed Source admission')
focused = counts('focused', 3)
prepared = counts('preparation-focused', 5)
preceding = counts('preceding-focused', 26)
regression = counts('regression', 31)
require(focused['reload.formal-migration-test'] >= 120 and regression['formal.facade-test'] >= 208, 'migration semantics and common facade exercised')
require(prepared['system.formal-preparation-test'] >= 109 and preceding['veritas.ledger-large-terms-test'] >= 21, 'prior binding and payload boundaries')
for stage in ('focused', 'preparation-focused', 'preceding-focused', 'regression', 'examples', 'ledger-write', 'ledger-read'):
    command = read(E / (stage + '-command.json'))
    require(str(sdk / 'bin/bl') in command, 'exact SDK: ' + stage)
    runtime = read(E / (stage + '-runtime.json'))
    require(runtime['retired'] and all(not Path(p).exists() for p in runtime['paths']), 'retired owned runtime: ' + stage)
    require(all(any(command[i:i+2] == ['-u', var] for i in range(len(command)-1))
                for var in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH')), 'default SDK artifacts: ' + stage)
paired = 0
for name in ('advanced', 'features', 'native'):
    now = read(E / 'regression' / (name + '.json'))
    old = {row['id']: row for row in read(P / 'evidence/query-preparation/regression' / (name + '.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'healthy matrix: ' + name)
    require(old.keys() == {row['id'] for row in now['cases']}, 'same preceding cases')
    for row in now['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same original question: ' + row['id'])
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')), 'same preceding verdict')
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'matrix SDK provenance')
    paired += len(now['cases'])
require(paired == 187, 'all preceding paired questions')
example = read(E / 'examples.json')
require(not example['research-import-path'] and not Path(example['cwd']).is_relative_to(R)
        and '-p' not in read(E / 'examples-command.json'), 'SDK-only consumer in unrelated directory')
require(len(example['cases']) == 6, 'three new subjects on both backends')
for kind in ('good', 'bad', 'source'):
    rows = [row for row in example['cases'] if row['kind'] == kind]
    require({row['backend'] for row in rows} == {'z3', 'oxiz'} and len({row['question'] for row in rows}) == 1
            and len({row['admission-question'] for row in rows}) == 1, 'same complete questions: ' + kind)
    for row in rows:
        result = row['result']
        require(result['status'] == ('refuted' if kind == 'bad' else 'checked') and result['verified'] is (kind != 'bad'), 'precise verified truth')
        require(result['compiler-proof-authority'] is False and result['delivery-authority'] is False, 'no authority')
        native = result['backend']['property']
        require(native['identity']['artifacts']['sdk'] == pin['sdk'] and native['backend']['name'] == row['backend'], 'actual native provenance')
        require(native['certificate']['status'] == 'not-checked', 'native absence stays unchecked')
        require(result['admission']['checking']['status'] == 'checked-data-connection', 'independent admission')
        if kind == 'bad':
            require(result['counterexample']['checking']['status'] == 'checked-data-connection' and native['verdict'] == 'refuted', 'original counterexample replay')
        else:
            require(result['proof']['checking']['status'] == 'checked' and native['verdict'] == 'proved', 'fresh conditional proof')
        if kind == 'good':
            require(row['limited']['status'] == 'uncertified' and row['limited']['verified'] is None
                    and row['limited']['backend']['property']['verdict'] == 'proved', 'native proof cannot fill missing certificate')
run = example['source-replay']
require(run['status'] == 'valid' and run['actual']['value'] == 5 and run['actual']['module-loaded'] is False, 'actual source invocation and retirement')
a, b = read(E / 'ledger-write.json'), read(E / 'ledger-read.json')
require(a['process'] != b['process'] and len(a['rows']) == len(b['rows']) == 4 and a['rows'] == b['rows'], 'durable fresh-process reconstruction')
for report in (a, b):
    require(report['managed-query-calls'] == 0 and report['managed-query-scope'] == 'record-rechecking'
            and report['compiler-proof-authority'] is False and report['delivery-authority'] is False, 'pure record rechecking scope')
floor, preflight = read(E / 'produced-compiler.json'), read(E / 'source-preflight.json')
require(floor['status'] == 'passed' and floor['sdk'] == pin['sdk'] and floor['files'] == 141, 'complete compiler artifact floor')
require(preflight['root'] == pin['source'] and preflight['runtime'] == pin['sdk'], 'immutable source preflight')
require(all(preflight[k]['modality'] == 'exhausted' and preflight[k]['complete'] for k in ('beam-selection', 'declaration-cases'))
        and not any(preflight[k] for k in ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')), 'exhaustive source gates')
require('SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text(), 'negative controls')
counts_by_stage = {'focused': focused, 'preparation-focused': prepared, 'preceding-focused': preceding, 'regression': regression}
total = sum(sum(rows.values()) for rows in counts_by_stage.values())
report = {'schema': 'enchant.formal.migration-qualification.v1', 'status': 'passed', 'checkpoint': 40,
          'sdk_pin': pin, 'source': snapshot, 'checked_programs': checked, 'assertion_executions': total,
          'runs': counts_by_stage, 'preceding_paired_questions': paired, 'new_paired_migration_subjects': 3,
          'sdk_only': True, 'durable_fresh_process_rechecking': True,
          'record_rechecking_managed_query_calls': 0, 'examples_sha256': sha(E / 'examples.json'),
          'scope': 'Declared exact Bool/Int message relations, independent term evidence and one observed Source invocation; no mailbox delivery or universal compiler preservation.',
          'compiler_proof_authority': False, 'delivery_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'checkpoint': 40, 'assertions': total, 'preceding_paired': paired, 'new_paired': 3}))
