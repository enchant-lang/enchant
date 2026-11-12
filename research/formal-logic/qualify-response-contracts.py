"""Bind response relations, source replay and stored evidence to one SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/response-contracts'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, reason):
    if not ok:
        raise AssertionError(reason)


def counts(name, files):
    log = (E / name).read_text()
    values = {n: int(c) for n, c in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
    require(len(values) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in log,
            'complete successful run: ' + name)
    return values


pin = read(E / 'sdk-candidate.json')
sdk, source = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'] and meta['source'] == str(source), 'SDK source and descriptor')
production = read(E / 'preparation-result.json')
require(production['ok'] is True and production['value']['output'] == pin['sdk']
        and production['value']['operation'] == 'sdk', 'managed immutable SDK production')
previous = read(Path(read(E / 'baseline-sdk-pin.json')['sdk']) / 'artifact.json')
require(meta['compiler'] == previous['compiler'] and meta['formalWorker'] == previous['formalWorker'], 'unchanged compiler and native worker')
snapshot = read(E / 'sdk-source-pin.json')
require(snapshot['sdk_pin'] == pin, 'same implementation SDK')
for name, digest in snapshot['source_sha256'].items():
    require(sha(R / name) == digest and sha(source / name) == digest, 'exact implemented SDK source: ' + name)
    committed = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)
    require(hashlib.sha256(committed).hexdigest() == digest, 'committed implementation: ' + name)
checked = read(E / 'check-source-pin.json')
for name, digest in checked['source_sha256'].items():
    require(sha(R / name) == digest, 'checked program: ' + name)
    committed = subprocess.check_output(['git', 'show', checked['code_commit'] + ':' + name], cwd=R)
    require(hashlib.sha256(committed).hexdigest() == digest, 'committed check: ' + name)
units = read(sdk / 'unit-store/unit-index.json')['units']
require('formal.integer-optimize' in units and 'formal.optimize' not in units, 'integer search does not shadow the research Core optimizer')
require(not (source / 'priv/lib/formal/optimize.bl').exists(), 'removed conflicting canonical source')
floor, preflight = (read(E / n) for n in ('produced-compiler.json', 'source-preflight.json'))
require(floor['status'] == 'passed' and floor['sdk'] == pin['sdk'] and floor['files'] == 141, 'complete produced compiler floor')
require(preflight['root'] == str(source) and preflight['runtime'] == str(sdk), 'actual immutable preflight source and runtime')
require(all(preflight[k]['modality'] == 'exhausted' and preflight[k]['complete'] is True
            for k in ('beam-selection', 'declaration-cases'))
        and not any(preflight[k] for k in ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')), 'complete source preflight')
require('SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text(), 'preflight refusal controls')
require('0 passed, 12 failed' in (E / 'baseline-checks.txt').read_text()
        and '0 passed, 5 failed' in (E / 'assumption-baseline-checks.txt').read_text(), 'retained preceding SDK defects')
require('sdk_forwarder_route_changed' in (E / 'formal-regression-checks.txt').read_text()
        and read(E / 'formal-regression-1-stop.json')['status'] == 'stopped', 'retained incomplete namespace-collision run')
focused, regression = counts('focused-current-checks.txt', 24), counts('regression-current-checks.txt', 31)
require(focused['veritas.response-boundary-baseline-test'] == 12
        and focused['veritas.assumption-domain-baseline-test'] == 5
        and focused['veritas.response-terms-test'] >= 144
        and focused['veritas.response-optimize-test'] >= 102
        and focused['veritas.response-server-test'] >= 41, 'new meaningful response and scope checks')
paired = 0
for name in ('advanced', 'features', 'native'):
    now = read(E / 'regression-current' / (name + '.json'))
    old = {x['id']: x for x in read(P / 'evidence/veritas-terms/regression-current' / (name + '.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'healthy native matrix: ' + name)
    require(old.keys() == {x['id'] for x in now['cases']}, 'same preceding cases')
    for row in now['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete question: ' + row['id'])
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')), 'same preceding native capability')
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'matrix SDK provenance')
    paired += len(now['cases'])
require(paired == 187, '187 paired preceding questions')
for name in ('focused-current-command.json', 'regression-current-command.json', 'examples-command.json', 'ledger-write-command.json', 'ledger-read-command.json'):
    command = read(E / name)
    require(str(sdk / 'bin/bl') in command, 'exact SDK command: ' + name)
    require(all(any(command[i:i+2] == ['-u', var] for i in range(len(command)-1))
                for var in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH')), 'default SDK native artifacts')
example = read(E / 'examples.json')
require(example['research-import-path'] is False and not Path(example['cwd']).is_relative_to(R)
        and '-p' not in read(E / 'examples-command.json'), 'SDK-only unrelated-directory consumer')
expected = ['witnessed', 'witnessed', 'witnessed', 'witnessed', 'solver-claim', 'vacuous', 'witnessed', 'solver-claim', 'solver-claim', 'candidate']
require([x['backend'] for x in example['native']] == ['z3', 'oxiz'], 'both backends')
for engine in example['native']:
    rows = engine['rows']
    require([x['modality'] for x in rows] == expected, 'SDK-only response distinctions')
    require(rows[1]['value'] == {'flag': False} and rows[2]['value']['real'] == {'formal/real': [1, 3]}, 'native BL mathematical and Boolean values')
    require(rows[8]['value'] == {'x': -41} and rows[8]['feasibility'] == 'witnessed'
            and rows[8]['optimality'] == 'solver-claim', 'separate global-boundary evidence')
    require(engine['retained-answer'] and engine['retained-semantic-assumption'], 'memo and persistent-domain checks')
    require(all(x['artifacts']['sdk'] == pin['sdk'] and x['compiler-proof-authority'] is False for x in rows), 'example provenance and authority')
require([x['question'] for x in example['native'][0]['rows'][:8]] == [x['question'] for x in example['native'][1]['rows'][:8]], 'same new complete questions')
write, reread = (read(E / n) for n in ('ledger-write.json', 'ledger-read.json'))
require(write['mode'] == 'write' and reread['mode'] == 'read' and write['process'] != reread['process']
        and write['rows'] == reread['rows'] == 2 and write['claims'] == reread['claims']
        and write['compound-evidence-retained'] and reread['compound-evidence-retained'], 'fresh-process compound ledger evidence')
report = {'schema': 'enchant.formal.response-contracts-qualification.v1', 'checkpoint': 37, 'sdk_pin': pin,
          'source': snapshot, 'checks': {'focused': focused, 'regression': regression,
            'focused_assertions': sum(focused.values()), 'regression_assertions': sum(regression.values())},
          'bl_assertions': sum(focused.values()) + sum(regression.values()), 'unchanged_paired_questions': paired,
          'sdk_only': True, 'durable_ledger_fresh_process': True,
          'native_model_completion': {'z3': 'materialized unconstrained integer', 'oxiz': 'opaque unconstrained integer remains candidate'},
          'source_connection': 'reviewed-not-mechanized', 'compiler_proof_authority': False,
          'evidence_sha256': {n: sha(E / n) for n in ('focused-current-checks.txt', 'regression-current-checks.txt',
             'examples.json', 'ledger-write.json', 'ledger-read.json', 'produced-compiler.json', 'source-preflight.json')}}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'checkpoint': 37, 'assertions': report['bl_assertions'], 'paired_questions': paired}))
