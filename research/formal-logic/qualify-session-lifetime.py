"""Bind native lifetime checks to their immutable SDK and original red baseline."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/session-lifetime'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise AssertionError(why)


def counts(path, expected):
    text = path.read_text()
    result = {name: int(n) for name, n in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    require(set(result) == expected and all(result.values()), 'expected files: ' + str(path))
    require(f'{len(expected)} file(s) passed, 0 failed, 0 incoherent' in text, 'successful complete run')
    return result


candidate = read(E / 'sdk-candidate.json')
pin = read(P / 'sdk-pin.json')
require(all(candidate[k] == pin[k] for k in ('sdk', 'source', 'descriptor_sha256')), 'selected exact candidate')
sdk = Path(pin['sdk'])
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'], 'immutable SDK descriptor')
require(read(sdk / 'artifact.json')['source'] == pin['source'], 'actual SDK source')
for name, digest in candidate['source_sha256'].items():
    require(sha(R / name) == digest, 'unchanged qualified code: ' + name)
    require(hashlib.sha256(subprocess.check_output(['git', 'show', candidate['code_commit'] + ':' + name], cwd=R)).hexdigest()
            == digest, 'committed qualified code: ' + name)
    if name.startswith(('priv/', 'native/')):
        require(sha(Path(candidate['engine_source']) / name) == digest, 'captured engine source: ' + name)
        require(sha(Path(pin['source']) / name) == digest, 'SDK actual source: ' + name)
previous = read(E / 'previous-sdk-pin.json')
prior_source = Path(previous['source'])
formal_files = sorted((R / 'priv/lib/formal').glob('*.bl'))
for path in formal_files:
    if path.name != 'backend.bl':
        require(sha(path) == sha(prior_source / path.relative_to(R)), 'unchanged other canonical formal module')
for name in candidate['source_sha256']:
    if name.startswith('native/ports/formal_worker/'):
        require(sha(R / name) == sha(prior_source / name), 'unchanged native worker source')
build = read(E / 'managed-build-result.json')
require(build['id'] == candidate['managed_handle'] and build['status'] == 'succeeded'
        and build['exit_code'] == 0 and build['spawn_count'] == 1, 'one successful managed SDK build')
compiler = read(E / 'produced-compiler.json')
require(compiler['status'] == 'passed' and compiler['sdk'] == pin['sdk'] and compiler['files'] == 141
        and compiler['manifest_sha256'] == read(P / 'evidence/packaged-worker/produced-compiler.json')['manifest_sha256'],
        'same complete P/B/C-qualified compiler floor')
preflight = read(E / 'source-preflight.json')
require(preflight['beam-selection']['modality'] == 'proven' and not any(preflight[k] for k in
        ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')),
        'complete Source preflight')
baseline = read(E / 'baseline-source-pin.json')
require(baseline['sdk_pin'] == previous, 'baseline on previous exact SDK')
for name, digest in baseline['source_sha256'].items():
    require(hashlib.sha256(subprocess.check_output(['git', 'show', baseline['code_commit'] + ':' + name], cwd=R)).hexdigest()
            == digest, 'committed original test fixture')
require('148 passed, 21 failed' in (E / 'baseline-checks.txt').read_text(), 'real behavioral red baseline')
focused = counts(E / 'focused-checks.txt', {'system.formal-lifetime-test', 'system.formal-artifact-test',
    'source-formal-artifact-test', 'system.effect-test', 'system.formal-effect-test', 'source-effect-test',
    'system.formal-context-owner-test', 'system.formal-answer-test', 'system.formal-oracle-test'})
require(focused['system.formal-lifetime-test'] == 183 and sum(focused.values()) == 686,
        'native lifetime cases and preceding interface checks')
regression = counts(E / 'regression-checks.txt', {'system.oracle-test', 'system.system-test'} |
    {'formal.' + name + '-test' for name in ('query', 'backend', 'kernel', 'certificate', 'core', 'record',
     'protocol', 'protocol-trace', 'contract', 'loop', 'translation', 'api', 'facade', 'witness',
     'core-counterexamples', 'advanced', 'features', 'native', 'context', 'selected-runtime')})
require(sum(regression.values()) == 7086, 'complete term and formal regression')
for name in ('focused-command.json', 'regression-command.json'):
    cmd = read(E / name)
    require(str(sdk / 'bin/bl') in cmd, 'actual candidate command')
    for variable in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH'):
        require(any(cmd[i:i+2] == ['-u', variable] for i in range(len(cmd)-1)), 'no external artifact pin')
total = 0
for name in ('advanced', 'features', 'native'):
    current = read(E / 'regression' / (name + '.json'))
    old = {row['id']: row for row in read(P / 'evidence/packaged-worker/regression' / (name + '.json'))['cases']}
    require(not current['disagreements'] and not current['invalid-models'], 'healthy paired matrix')
    require(old.keys() == {row['id'] for row in current['cases']}, 'same paired question set')
    for row in current['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete typed question')
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')),
                    'unchanged capability: ' + row['id'])
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'actual candidate matrix')
    total += len(current['cases'])
require(total == 187, 'all paired native questions')
files = sorted(set(candidate['source_sha256']) | {
    'research/formal-logic/SESSION-LIFETIME.md', 'research/formal-logic/qualify-session-lifetime.py'})
report = {'schema': 'enchant.formal.session-lifetime-qualification.v1', 'checkpoint': 33,
    'sdk_pin': pin, 'source': {'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
                             'sha256': {name: sha(R / name) for name in files}},
    'managed_build': build, 'compiler': compiler,
    'checks': {'focused': focused, 'regression': regression, 'total_assertions': 7772, 'failed': 0},
    'baseline': baseline, 'unchanged_paired_questions': total,
    'scope': ['post-start session setup inside cleanup bracket', 'monitored owner stop with exact-PID kill fallback',
              'actual native owner and OS death on return, exception, suspension and idle borrower loss',
              'fault-peer startup/exchange/deadline/cancellation checks', 'one complete bounded uncompressed ETF reply',
              'transport kind, phase and operation preserved'],
    'remaining': ['genuine hard-search cancellation qualification', 'bounded pool admission and complete reset semantics',
                  'remaining legacy/source Oracle migration', 'language totality and compiler/runtime preservation'],
    'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'checkpoint': 33, 'focused': 686, 'regression': 7086, 'paired_questions': total,
                  'compiler_proof_authority': False}))
