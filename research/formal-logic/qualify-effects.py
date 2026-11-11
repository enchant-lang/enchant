"""Bind managed handler behavior to committed code and one qualified SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/effects'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise AssertionError(why)


def counts(path, files):
    text = path.read_text()
    result = {name: int(n) for name, n in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    require(set(result) == files and all(result.values()), 'expected passing files: ' + str(path))
    require(f'{len(files)} file(s) passed, 0 failed, 0 incoherent' in text, 'complete successful run: ' + str(path))
    return result


pin, candidate = read(P / 'sdk-pin.json'), read(E / 'sdk-candidate.json')
require(all(pin[k] == candidate[k] for k in ('sdk', 'descriptor_sha256', 'source')), 'selected candidate SDK')
sdk = Path(pin['sdk'])
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256']
        and read(sdk / 'artifact.json')['source'] == pin['source'], 'immutable descriptor')
require(len(candidate['source_sha256']) == 24, 'complete formal/effect/oracle/host/world source inventory')
for name, digest in candidate['source_sha256'].items():
    require(sha(R / name) == sha(Path(pin['source']) / name) == digest, 'exact SDK source: ' + name)
    require(subprocess.check_output(['git', 'show', candidate['code_commit'] + ':' + name], cwd=R)
            == (R / name).read_bytes(), 'committed language source: ' + name)
build = read(E / 'managed-build-result.json')
require(build['id'] == candidate['managed_handle'] and build['status'] == 'succeeded'
        and build['exit_code'] == 0 and build['spawn_count'] == 1, 'successful single managed production')
compiler = read(E / 'produced-compiler.json')
require(compiler['sdk'] == pin['sdk'] and compiler['status'] == 'passed'
        and compiler['generations'] == ['P', 'B', 'C'], 'qualified SDK compiler generations')
preflight = read(E / 'source-preflight.json')
require(preflight['beam-selection']['modality'] == 'proven'
        and not any(preflight[k] for k in ('source-errors', 'target-dependency-errors', 'require-cycles',
                                          'sources_changed_during_analysis')), 'static Source preflight')
require('6 passed, 14 failed' in (E / 'baseline-checks.txt').read_text(), 'retained process boundary failures')
focused = counts(E / 'focused-checks.txt', {'system.effect-test', 'system.formal-effect-test', 'source-effect-test',
    'system.formal-context-owner-test', 'system.formal-answer-test', 'system.formal-oracle-test'})
require({k: focused[k] for k in ('system.formal-context-owner-test', 'system.formal-answer-test',
                                'system.formal-oracle-test')}
        == {'system.formal-context-owner-test': 136, 'system.formal-answer-test': 134,
            'system.formal-oracle-test': 86}, 'preceding SDK interface assertions')
runtime = counts(E / 'runtime-checks.txt', {'native-execution-' + name + '-test' for name in
    ('context', 'scoped-context', 'managed-context', 'context-race', 'start-context', 'actor-pin',
     'actor-grant-pin', 'actor-frame', 'managed-frame', 'frame-attestation')} | {'proc-framework-test'})
capacity = counts(E / 'capacity-checks.txt', {'native-execution-context-capacity-test'})
regression = counts(E / 'regression-checks.txt', {'system.oracle-test', 'system.system-test'} |
    {'formal.' + name + '-test' for name in ('query', 'backend', 'kernel', 'certificate', 'core', 'record',
     'protocol', 'protocol-trace', 'contract', 'loop', 'translation', 'api', 'facade', 'witness',
     'core-counterexamples', 'advanced', 'features', 'native', 'context', 'selected-runtime')})
require(sum(regression.values()) == 7086, 'complete targeted formal regression')
matrices = {}
for name in ('advanced', 'features', 'native'):
    current = read(E / 'regression' / (name + '.json'))
    old = {row['id']: row for row in read(P / 'evidence/native-contexts/regression' / (name + '.json'))['cases']}
    require(not current['disagreements'] and not current['invalid-models'], 'healthy paired native comparison')
    require(old.keys() == {row['id'] for row in current['cases']}, 'same paired questions')
    for row in current['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same portable question')
        for engine in ('z3', 'oxiz'):
            require(all(row[engine][k] == old[row['id']][engine][k] for k in ('solver-status', 'verdict')),
                    'unchanged native capability: ' + row['id'])
            require(row[engine]['identity']['sdk'] == pin['sdk'], 'exact native SDK')
    matrices[name] = {'questions': len(current['cases']), 'summary': current['summary']}
require(sum(x['questions'] for x in matrices.values()) == 187, 'all previous native questions')
examples = read(E / 'examples.json')['results']
require([row['backend-choice'] for row in examples['managed']] == ['z3', 'oxiz'], 'both backend choices')
for row in examples['managed']:
    require(row['native-paths'] == 'unavailable' and row['caller-handler-restored']
            and row['portable-question'], 'handled execution and caller restoration')
    require(set(row['answers']) == {'child', 'future', 'registration', 'actor'}, 'all managed example boundaries')
    require(all(answer == {'verdict': 'sat', 'x': 7, 'validation': 'valid', 'certificate': 'not-checked'}
                for answer in row['answers'].values()), 'typed replay and unchanged certificate status')
require(examples['named'] == {'submitted-work': 42, 'caller-default': 40, 'caller-restored': True}
        and examples['continuation-capture'] is False, 'generic named synchronous effect')
qualified = [R / name for name in candidate['source_sha256']]
qualified += [R / 'test/bl/system' / name for name in ('effect_test.bl', 'formal_effect_test.bl',
    'formal_context_owner_test.bl', 'formal_answer_test.bl', 'formal_oracle_test.bl')]
qualified += [R / 'test/bl/source_effect_test.bl', R / 'test/bl/proc_framework_test.bl']
qualified += [P / name for name in ('EFFECTS.md', 'src/formal/effect-examples.bl', 'effects-check.bl', 'qualify-effects.py')]
report = {'schema': 'enchant.formal.effect-qualification.v1', 'checkpoint': 31, 'sdk_pin': pin,
    'sdk_source_commit': candidate['code_commit'], 'managed_build': build, 'compiler': compiler,
    'source': {'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
               'sha256': {str(path.relative_to(R)): sha(path) for path in qualified}},
    'baseline': {'passed': 6, 'failed': 14, 'errored': 0, 'sdk_pin': read(E / 'previous-sdk-pin.json')},
    'checks': {'focused': focused, 'runtime': runtime, 'capacity': capacity, 'regression': regression,
               'total_assertions': sum(sum(x.values()) for x in (focused, runtime, capacity, regression)), 'failed': 0},
    'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
    'z3_library_sha256': sha(sdk / 'image/priv/z3/bin/libz3.so'), 'matrices': matrices,
    'unchanged_paired_questions': 187,
    'scope': ['synchronous named method tables', 'submission snapshots for managed work and native actors',
              'direct callable modules and explicit outside dependencies retained before publication',
              'restoration for nested scopes and reused workers', 'Source world and SDK framework boundaries',
              'Oracle script/query methods and correlated managed legacy fanout'],
    'remaining': ['effect typing, continuation capture and formal runtime preservation',
                  'remaining legacy/source oracle migration and native worker packaging',
                  'compiler preservation and language-wide totality'], 'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'checkpoint': 31, 'assertions': report['checks']['total_assertions'],
                  'unchanged_native_questions': 187, 'compiler_proof_authority': False}))
