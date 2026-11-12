"""Bind complete native replies and actual response replay to one immutable SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/answer-binding'


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
require('1 passed, 9 failed' in (E / 'baseline-checks.txt').read_text(), 'retained preceding SDK boundary defects')
require('Keys can be up to 65535 bytes long' in (E / 'candidate-1/ledger-write-checks.txt').read_text(), 'retained durable index-key failure')
focused, regression = counts('focused-checks.txt', 26), counts('regression-checks.txt', 31)
require(focused['veritas.ledger-large-terms-test'] >= 21
        and focused['veritas.answer-binding-baseline-test'] == 10
        and focused['veritas.ledger-test'] >= 42
        and focused['veritas.response-boundary-baseline-test'] == 12
        and focused['veritas.assumption-domain-baseline-test'] == 5
        and focused['veritas.response-terms-test'] >= 144
        and focused['veritas.response-optimize-test'] >= 102
        and focused['veritas.response-server-test'] >= 41, 'new meaningful response and scope checks')
paired = 0
for name in ('advanced', 'features', 'native'):
    now = read(E / 'regression' / (name + '.json'))
    old = {x['id']: x for x in read(P / 'evidence/response-contracts/regression-current' / (name + '.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'healthy native matrix: ' + name)
    require(old.keys() == {x['id'] for x in now['cases']}, 'same preceding cases')
    for row in now['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete question: ' + row['id'])
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')), 'same preceding native capability')
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'matrix SDK provenance')
    paired += len(now['cases'])
require(paired == 187, '187 paired preceding questions')
for name in ('focused-command.json', 'regression-command.json', 'examples-command.json', 'ledger-write-command.json', 'ledger-read-command.json'):
    command = read(E / name)
    require(str(sdk / 'bin/bl') in command, 'exact SDK command: ' + name)
    require(all(any(command[i:i+2] == ['-u', var] for i in range(len(command)-1))
                for var in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH')), 'default SDK native artifacts')
example = read(E / 'examples.json')
require(example['research-import-path'] is False and not Path(example['cwd']).is_relative_to(R)
        and '-p' not in read(E / 'examples-command.json'), 'SDK-only unrelated-directory consumer')
require([x['backend'] for x in example['native']] == ['z3', 'oxiz'], 'both backends')
for engine in example['native']:
    require(engine['native-question-bound'] and engine['good'] == 'witnessed'
            and engine['projection-replay'] == 'valid', 'native full question and valid response point')
    require(engine['foreign-model'] == engine['foreign-absence'] == 'error'
            and engine['corrupt-point'] == 'candidate' and engine['corrupt-point-replay'] == 'invalid',
            'foreign answers and decoded points never become witnesses or absence claims')
    require(engine['artifacts']['sdk'] == pin['sdk'] and engine['compiler-proof-authority'] is False,
            'example provenance and authority')
require(example['native'][0]['question'] == example['native'][1]['question'], 'same new question across both backends')
write, reread = (read(E / n) for n in ('ledger-write.json', 'ledger-read.json'))
require(write['mode'] == 'write' and reread['mode'] == 'read' and write['process'] != reread['process']
        and write['rows'] == reread['rows'] == 2 and write['claims'] == reread['claims']
        and write['compound-evidence-retained'] and reread['compound-evidence-retained'], 'fresh-process compound ledger evidence')
report = {'schema': 'enchant.formal.answer-binding-qualification.v1', 'checkpoint': 38, 'sdk_pin': pin,
          'source': snapshot, 'checks': {'focused': focused, 'regression': regression,
            'focused_assertions': sum(focused.values()), 'regression_assertions': sum(regression.values())},
          'bl_assertions': sum(focused.values()) + sum(regression.values()), 'unchanged_paired_questions': paired,
          'sdk_only': True, 'durable_ledger_fresh_process': True,
          'native_reply_binding': 'complete effective question',
          'response_point_validation': 'all original assertions counterexample goal and concrete pins',
          'durable_payload': 'content-addressed datom file using its existing value codec',
          'source_connection': 'reviewed-not-mechanized', 'compiler_proof_authority': False,
          'evidence_sha256': {n: sha(E / n) for n in ('focused-checks.txt', 'regression-checks.txt',
             'examples.json', 'ledger-write.json', 'ledger-read.json', 'produced-compiler.json', 'source-preflight.json')}}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'checkpoint': 38, 'assertions': report['bl_assertions'], 'paired_questions': paired}))
