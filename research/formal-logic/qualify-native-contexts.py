"""Qualify owner-held native contexts, native availability and the exact SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/native-contexts'


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
require(all(pin[k] == candidate[k] for k in ('sdk', 'descriptor_sha256', 'source')), 'exact qualified SDK selection')
sdk = Path(pin['sdk'])
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256']
        and read(sdk / 'artifact.json')['source'] == pin['source'], 'immutable descriptor')
require(len(candidate['source_sha256']) == 20, 'nineteen canonical formal modules and oracle')
for name, digest in candidate['source_sha256'].items():
    require(sha(R / name) == sha(Path(pin['source']) / name) == digest, 'exact canonical SDK source: ' + name)
    require((R / name).read_bytes() == subprocess.check_output(['git', 'show', candidate['code_commit'] + ':' + name], cwd=R),
            'committed SDK source: ' + name)
build = read(E / 'managed-build-result.json')
require(build['id'] == candidate['managed_handle'] and build['status'] == 'succeeded'
        and build['exit_code'] == 0 and build['spawn_count'] == 1, 'successful managed build')
require(build['truncated'] == candidate['build_stdout_truncated'], 'accurate build transcript scope')
preflight = read(E / 'source-preflight.json')
require(preflight['beam-selection']['modality'] == 'proven'
        and not any(preflight[k] for k in ('source-errors', 'target-dependency-errors', 'require-cycles',
                                          'sources_changed_during_analysis')), 'source preflight')
baseline = (E / 'baseline-checks.txt').read_text()
require('12 passed, 20 failed' in baseline and '0 file(s) passed, 1 failed, 0 incoherent' in baseline,
        'preserved original consistency failures')
first = (E / 'candidate-1-focused-checks.txt').read_text()
require('system.formal-context-owner-test  127 passed, 2 failed' in first
        and 'system.formal-answer-test  133 passed, 1 failed' in first
        and 'system.formal-oracle-test  86 passed' in first, 'first candidate failures retained')
first_build = read(E / 'candidate-1-build-result.json')
require(first_build['status'] == 'succeeded' and first_build['exit_code'] == 0, 'first candidate build succeeded')
focused = counts(E / 'focused-checks.txt')
require(focused == {'system.formal-context-owner-test': 136, 'system.formal-answer-test': 134,
                     'system.formal-oracle-test': 86}
        and '3 file(s) passed, 0 failed, 0 incoherent' in (E / 'focused-checks.txt').read_text(), 'public SDK qualification')
regression = counts(E / 'regression-checks.txt')
expected = {'system.oracle-test', 'system.system-test'} | {'formal.' + name + '-test' for name in
    ('query', 'backend', 'kernel', 'certificate', 'core', 'record', 'protocol', 'protocol-trace',
     'contract', 'loop', 'translation', 'api', 'facade', 'witness', 'core-counterexamples',
     'advanced', 'features', 'native', 'context', 'selected-runtime')}
require(regression.keys() == expected and sum(regression.values()) == 7086
        and '22 file(s) passed, 0 failed, 0 incoherent' in (E / 'regression-checks.txt').read_text(), 'full targeted regression')
matrices = {}
for name in ('advanced', 'features', 'native'):
    current = read(E / 'regression' / (name + '.json'))
    old = {row['id']: row for row in read(P / 'evidence/answer-integrity/regression' / (name + '.json'))['cases']}
    require(not current['disagreements'] and not current['invalid-models'], 'healthy native comparison')
    require(old.keys() == {row['id'] for row in current['cases']}, 'same original cases')
    for row in current['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'unchanged question identity')
        for engine in ('z3', 'oxiz'):
            require(all(row[engine][key] == old[row['id']][engine][key] for key in ('solver-status', 'verdict')),
                    'unchanged native availability: ' + row['id'])
            require(row[engine]['identity']['sdk'] == pin['sdk'], 'exact native SDK identity')
    matrices[name] = {'questions': len(current['cases']), 'summary': current['summary']}
require(sum(row['questions'] for row in matrices.values()) == 187, 'all existing native questions')
examples = read(E / 'examples.json')
require({row['backend'] for row in examples['rows']} == {'z3', 'oxiz'} and len(examples['rows']) == 2, 'paired owner examples')
for row in examples['rows']:
    require(row['raw']['native-load'] == 'accepted' and row['raw']['portable-query'] ==
            {'verdict': 'error', 'phase': 'frontend', 'solver-status': 'not-run'}
            and row['raw']['after-reset'] == 'refuted', 'raw mutation refused and reset recovers')
    require(row['raw']['identity']['sdk'] == pin['sdk'], 'examples use exact SDK')
    require(row['forgotten'] == {'handler-verdict': 'unknown', 'retained-assumptions': 1,
            'retained-labels': ['context/0/known-x'], 'after-mirror-change': 'proved', 'question-is-portable': True},
            'owner supplies assumptions independently of the client mirror')
    require(row['restored'] == {'fallback': 'not-run', 'verdict': 'error', 'mirror-revision': 0, 'owner-revision': 1},
            'restoring mirror cannot restore owner revision')
    require(row['revision'] == {'before': 0, 'after': 1, 'stale-scope': 'context-changed',
            'native-checks-before': 1, 'native-checks-after': 2, 'rejected-exchange-native-checks': 0},
            'stale scope refused without a native check')
qualified = [R / name for name in candidate['source_sha256']]
qualified += [R / 'test/bl/system' / name for name in
              ('formal_context_owner_test.bl', 'formal_answer_test.bl', 'formal_oracle_test.bl')]
qualified += [P / name for name in ('NATIVE-CONTEXTS.md', 'src/formal/native-context-examples.bl',
                                   'native-contexts-check.bl', 'qualify-native-contexts.py')]
report = {
    'schema': 'enchant.formal.native-context-qualification.v1', 'checkpoint': 30,
    'sdk_pin': pin, 'sdk_source_commit': candidate['code_commit'], 'managed_build': build,
    'source': {'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
               'sha256': {str(path.relative_to(R)): sha(path) for path in qualified}},
    'baseline': {'checks': {'passed': 12, 'failed': 20, 'errored': 0},
                 'code_commit': read(E / 'source-code-pin.json')['baseline_code_commit'],
                 'sdk': read(E / 'previous-sdk-pin.json')},
    'candidate_1': {'assertions_passed': 346, 'assertions_failed': 3,
                    'cause': 'fixture domain assertion and unsupported-result retirement projection'},
    'checks': {'focused_files': focused, 'focused_assertions': sum(focused.values()),
               'regression_files': regression, 'regression_assertions': sum(regression.values()), 'failed': 0},
    'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
    'z3_library_sha256': sha(sdk / 'image/priv/z3/bin/libz3.so'),
    'matrices': matrices, 'unchanged_paired_questions': 187,
    'scope': ['native-owner registry, assumptions, generation and revision',
              'complete question built from authoritative owner assumptions',
              'same-turn owner/generation/revision check before a scoped exchange',
              'raw transport invalidates portable accounting until managed reset',
              'client atom retained only as diagnostic mirror',
              'post-execution identity matching separate from liveness and native refusal status',
              'borrower-only context operations and owner retirement cleanup'],
    'remaining': ['automatic oracle handler inheritance with executable custody',
                  'remaining source/legacy oracle migration and native worker packaging',
                  'universal implementation, compiler/runtime preservation and arbitrary Erlang introspection'],
    'compiler_proof_authority': False,
}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'checkpoint': 30, 'focused': sum(focused.values()), 'regression': sum(regression.values()),
                  'unchanged_native_questions': 187, 'compiler_proof_authority': False}, indent=2))
