"""Audit the typed answer boundary against the saved failure and immutable SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/answer-integrity'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def counts(path):
    return {name: int(n) for name, n in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', path.read_text())}


pin = read(P / 'sdk-pin.json')
candidate = read(E / 'sdk-candidate.json')
require(all(pin[k] == candidate[k] for k in ('sdk', 'descriptor_sha256', 'source')), 'exact selected SDK')
sdk = Path(pin['sdk'])
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256']
        and read(sdk / 'artifact.json')['source'] == pin['source'], 'immutable artifact descriptor')
for name, digest in candidate['source_sha256'].items():
    require(sha(R / name) == sha(Path(pin['source']) / name) == digest, 'matching SDK source: ' + name)
    require((R / name).read_bytes() == subprocess.check_output(['git', 'show', candidate['code_commit'] + ':' + name], cwd=R),
            'committed SDK source: ' + name)
require(len(candidate['source_sha256']) == 20, 'nineteen formal modules and the oracle boundary')
build = read(E / 'managed-build-result.json')
require(build['id'] == candidate['managed_handle'] and build['status'] == 'succeeded'
        and build['exit_code'] == 0 and build['spawn_count'] == 1, 'successful managed build')
require(build['truncated'] == candidate['build_stdout_truncated'], 'accurate build transcript scope')
preflight = read(E / 'source-preflight.json')
require(preflight['beam-selection']['modality'] == 'proven'
        and not any(preflight[k] for k in ('source-errors', 'target-dependency-errors', 'require-cycles',
                                          'sources_changed_during_analysis')), 'source preflight passed')
require('13 passed, 27 failed' in (E / 'baseline-checks.txt').read_text()
        and '0 file(s) passed, 1 failed, 0 incoherent' in (E / 'baseline-checks.txt').read_text(),
        'original behavioral failures preserved')
require(read(E / 'baseline-summary.json')['checks'] == {'passed': 13, 'failed': 27, 'errored': 0}, 'baseline summary')
focused = counts(E / 'focused-checks.txt')
require(focused == {'system.formal-answer-test': 134, 'system.formal-oracle-test': 86}
        and '2 file(s) passed, 0 failed, 0 incoherent' in (E / 'focused-checks.txt').read_text(), 'focused SDK checks')
regression = counts(E / 'regression-checks.txt')
expected = {'system.oracle-test', 'system.system-test'} | {'formal.' + name + '-test' for name in
    ('query', 'backend', 'kernel', 'certificate', 'core', 'record', 'protocol', 'protocol-trace',
     'contract', 'loop', 'translation', 'api', 'facade', 'witness', 'core-counterexamples',
     'advanced', 'features', 'native', 'context', 'selected-runtime')}
require(regression.keys() == expected and sum(regression.values()) == 7086
        and '22 file(s) passed, 0 failed, 0 incoherent' in (E / 'regression-checks.txt').read_text(),
        'complete targeted regression')
matrices = {}
for name in ('advanced', 'features', 'native'):
    current = read(E / 'regression' / (name + '.json'))
    old = {row['id']: row for row in read(P / 'evidence/sdk-interface/regression' / (name + '.json'))['cases']}
    require(not current['disagreements'] and not current['invalid-models'], 'healthy native comparison')
    require(old.keys() == {row['id'] for row in current['cases']}, 'same original cases')
    for row in current['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'unchanged question')
        for engine in ('z3', 'oxiz'):
            require(all(row[engine][key] == old[row['id']][engine][key] for key in ('solver-status', 'verdict')),
                    'unchanged native result: ' + row['id'])
            require(row[engine]['identity']['sdk'] == pin['sdk'], 'exact SDK used for native regression')
    matrices[name] = {'questions': len(current['cases']), 'summary': current['summary']}
require(sum(row['questions'] for row in matrices.values()) == 187, 'all preceding paired questions')
examples = read(E / 'examples.json')
require(examples['handled'] == {'compiler-proof-authority': False, 'derived-next': 8,
    'execution': 'handled-in-beam-lisp', 'ill-sorted-contradiction': 'invalid-model',
    'observation-source': 'independent-replay', 'reported-next': 999, 'typed-bindings': 'invalid', 'wrong-phase': 'error'},
    'recorded pure handler behavior')
require(len(examples['equalities']) == 3
        and [row['oxiz']['verdict'] for row in examples['equalities']] == ['unsupported', 'proved', 'proved'],
        'exact additional OxiZ availability')
for row in examples['equalities']:
    require(row['independent-value'] is True and row['z3']['verdict'] == 'proved', 'recursive equality result')
    for engine in ('z3', 'oxiz'):
        require(row[engine]['certificate']['status'] == 'not-checked'
                and row[engine]['identity']['sdk'] == pin['sdk'], 'native answer scope')
require({row['backend'] for row in examples['contexts']} == {'z3', 'oxiz'}, 'paired context substitution')
for row in examples['contexts']:
    require(row['original-verdict'] == 'refuted'
            and all(row['changed-context'][key] == value for key, value in
                    [('verdict', 'error'), ('solver-status', 'not-run'), ('phase', 'frontend')])
            and 'context changed' in row['changed-context']['error'], 'fallback refused after tracked mutation')
qualified = [R / name for name in candidate['source_sha256']]
qualified += [R / 'test/bl/system' / name for name in ('formal_answer_test.bl', 'formal_oracle_test.bl')]
qualified += [P / name for name in ('ANSWER-INTEGRITY.md', 'SDK-INTERFACE.md', 'src/formal/answer-examples.bl',
                                   'answers-check.bl', 'qualify-answer-integrity.py')]
worker = R / 'research/oxiz-prototype/worker/target/release/formal-worker'
report = {
    'schema': 'enchant.formal.answer-integrity-qualification.v1', 'checkpoint': 29,
    'sdk_pin': pin, 'sdk_source_commit': candidate['code_commit'],
    'source': {'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
               'sha256': {str(path.relative_to(R)): sha(path) for path in qualified}},
    'managed_build': build, 'worker_sha256': sha(worker), 'z3_library_sha256': sha(sdk / 'image/priv/z3/bin/libz3.so'),
    'baseline': read(E / 'baseline-summary.json'),
    'checks': {'focused_files': focused, 'focused_assertions': sum(focused.values()),
               'regression_files': regression, 'regression_assertions': sum(regression.values()), 'failed': 0},
    'matrices': matrices, 'unchanged_paired_questions': 187, 'additional_ground_equality_questions': 3,
    'additional_native_verdicts': {'z3': [row['z3']['verdict'] for row in examples['equalities']],
                                  'oxiz': [row['oxiz']['verdict'] for row in examples['equalities']]},
    'source_documents': {'strings': 'https://smt-lib.org/theories-UnicodeStrings.shtml',
                         'floating_point': 'https://smt-lib.org/theories-FloatingPoint.shtml'},
    'scope': ['pure complete-question reply checking', 'sort-checked model replay and recursive FP equality',
              'phase/status meaning', 'effect-owned exact native delegation and reconstructed handler observations',
              'tracked context generation/assumption mutation refusal', 'logical sessions for derived procedures',
              'explicit handler claim evidence basis'],
    'remaining': ['general implementation soundness and compiler/runtime preservation',
                  'automatic oracle handler inheritance with executable custody',
                  'authoritative native-owner context accounting beyond mutable bookkeeping and raw transport escape hatches',
                  'remaining source/legacy oracle migration and native worker packaging'],
    'compiler_proof_authority': False,
}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'checkpoint': 29, 'focused': sum(focused.values()), 'regression': sum(regression.values()),
                  'unchanged_native_questions': 187, 'additional_ground_questions': 3, 'compiler_proof_authority': False}, indent=2))
