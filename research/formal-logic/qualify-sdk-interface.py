"""Audit the immutable SDK, public consumer checks and retained theory regression."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/sdk-interface'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


pin = read(P / 'sdk-pin.json')
candidate = read(E / 'sdk-candidate.json')
sdk = Path(pin['sdk'])
require(all(pin[k] == candidate[k] for k in ('sdk', 'descriptor_sha256', 'source')), 'selected exact candidate')
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'], 'immutable SDK descriptor')
require(read(sdk / 'artifact.json')['source'] == pin['source'], 'immutable SDK source')
source = Path(pin['source'])
matched = read(E / 'sdk-source-match.json')
require(matched['source'] == str(source) and matched['sdk'] == str(sdk), 'SDK source match receipt')
for name, digest in matched['sha256'].items():
    require(sha(R / name) == sha(source / name) == digest, 'exact canonical SDK source: ' + name)
    committed = subprocess.check_output(['git', 'show', candidate['code_commit'] + ':' + name], cwd=R)
    require(committed == (R / name).read_bytes(), 'committed SDK source: ' + name)
for name in ('candidate-1', 'candidate-2'):
    build = read(E / (name + '-build-result.json'))
    require(build['status'] == 'succeeded' and build['exit_code'] == 0 and build['error'] is None
            and build['spawn_count'] == 1 and len(build['steps']) == 1
            and build['steps'][0]['status'] == 'succeeded', 'successful managed build: ' + name)
    require(build['truncated'] and build['steps'][0]['truncated'], 'record stdout truncation: ' + name)
require(read(E / 'candidate-2-build-result.json')['id'] == candidate['managed_handle'], 'candidate build identity')
focused = (E / 'focused-checks.txt').read_text()
require('system.formal-oracle-test  86 passed' in focused and '1 file(s) passed, 0 failed, 0 incoherent' in focused,
        '86 public SDK assertions without research import paths')
original = (E / 'focused-checks-1.txt').read_text()
require('77 passed, 8 failed' in original, 'retain the original failed qualification')
checks = (E / 'regression-checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', checks)}
expected = {'system.oracle-test', 'system.system-test'} | {'formal.' + name + '-test' for name in
    ('query', 'backend', 'context', 'certificate', 'protocol', 'protocol-trace', 'contract', 'loop',
     'translation', 'api', 'advanced', 'features', 'native', 'core-counterexamples')}
require(counts.keys() == expected and '16 file(s) passed, 0 failed, 0 incoherent' in checks,
        'complete selected regression run')
matrices = {}
for name in ('advanced', 'features', 'native'):
    current = read(E / 'regression' / (name + '.json'))
    before = read(P / 'evidence/core-counterexamples/corpora' / (name + '.json'))
    require(not current['disagreements'] and not current['invalid-models'], 'no decisive disagreement or invalid model')
    old = {row['id']: row for row in before['cases']}
    require(old.keys() == {row['id'] for row in current['cases']}, 'same theory cases')
    for row in current['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same exact question terms')
        for engine in ('z3', 'oxiz'):
            require(row[engine]['verdict'] == old[row['id']][engine]['verdict']
                    and row[engine]['solver-status'] == old[row['id']][engine]['solver-status'],
                    'unchanged native verdict: ' + row['id'] + ' ' + engine)
            require(row[engine]['identity']['sdk'] == pin['sdk'], 'exact selected SDK during regression')
    matrices[name] = {'questions': len(current['cases']), 'summary': current['summary']}
require(sum(row['questions'] for row in matrices.values()) == 187, 'all 187 paired theory questions')
worker = R / 'research/oxiz-prototype/worker/target/release/formal-worker'
library = sdk / 'image/priv/z3/bin/libz3.so'
qualified = [R / name for name in matched['sha256']] + [P / name for name in
    ('SDK-INTERFACE.md', 'INTEGRATION.md', 'src/formal/api.bl', 'src/formal/contract.bl',
     'src/formal/loop.bl', 'src/formal/translation.bl', 'src/formal/review-host.bl', 'qualify-sdk-interface.py')]
qualified += [R / 'test/bl/system/formal_oracle_test.bl']
report = {
    'schema': 'enchant.formal.sdk-interface-qualification.v1', 'checkpoint': 28,
    'sdk_pin': pin, 'sdk_source_commit': candidate['code_commit'],
    'source': {'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
               'sha256': {str(path.relative_to(R)): sha(path) for path in qualified}},
    'worker_sha256': sha(worker), 'z3_library_sha256': sha(library),
    'checks': {'focused_assertions': 86, 'regression_files': counts,
               'regression_assertions': sum(counts.values()), 'failed': 0},
    'matrices': matrices, 'paired_questions': 187,
    'comparison_baseline': 'evidence/core-counterexamples/corpora (checkpoint 27, canonical term identities)',
    'candidate_1': {'build': 'succeeded', 'assertions_passed': 77, 'assertions_failed': 8,
                    'cause': 'optional context reply normalization and test fixture assumptions'},
    'build_stdout': 'both managed builds succeeded; their stdout ledgers are truncated',
    'scope': ['canonical SDK term/question/proof/state-model modules',
              'typed system.core arities and public common evidence',
              'complete typed query effect in the calling process',
              'owned logical/native contexts and bounded fallback lifetime',
              'custom legacy handlers bypass the shared script memo'],
    'remaining': ['automatic oracle handler inheritance across processes',
                  'derived native procedures use the common logical session',
                  'remaining legacy/source consumers and default text oracle migration',
                  'native worker SDK packaging and reusable worker pool',
                  'implementation soundness and universal compiler/runtime preservation'],
    'compiler_proof_authority': False,
}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'checkpoint': 28, 'focused': 86, 'regression': sum(counts.values()),
                  'paired_questions': 187, 'compiler_proof_authority': False}, indent=2))
