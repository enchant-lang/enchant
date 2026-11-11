"""Qualify term-native temporal consumers, their model laws and exact SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/temporal'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise AssertionError(why)


def committed(commit, name, digest):
    require(hashlib.sha256(subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R)).hexdigest()
            == digest, 'committed source: ' + name)


def counts(path):
    return {name: int(n) for name, n in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', path.read_text())}


candidate, pin = read(E / 'sdk-candidate.json'), read(P / 'sdk-pin.json')
require(all(candidate[k] == pin[k] for k in ('sdk', 'source', 'descriptor_sha256')), 'selected exact SDK')
sdk = Path(pin['sdk'])
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'], 'immutable SDK descriptor')
require(read(sdk / 'artifact.json')['source'] == pin['source'], 'actual SDK source')
corrected = read(E / 'check-source-pin.json')
require(set(corrected['source_sha256']) == {'test/bl/system/formal_temporal_test.bl'}, 'one test-only correction')
qualified = {}
for name, original in candidate['source_sha256'].items():
    committed(candidate['code_commit'], name, original)
    digest = corrected['source_sha256'].get(name, original)
    require(sha(R / name) == digest, 'unchanged qualified source: ' + name)
    if name in corrected['source_sha256']:
        committed(corrected['code_commit'], name, digest)
    if name.startswith(('priv/', 'native/', 'nix/', 'tooling/')):
        require(sha(Path(candidate['engine_source']) / name) == digest, 'captured engine input: ' + name)
    if name.startswith(('priv/', 'native/')):
        require(sha(Path(pin['source']) / name) == digest, 'actual SDK source: ' + name)
    qualified[name] = digest
prior = read(E / 'previous-sdk-pin.json')
for path in sorted((R / 'priv/lib/formal').glob('*.bl')):
    if path.name != 'temporal.bl':
        require(sha(path) == sha(Path(prior['source']) / path.relative_to(R)), 'unchanged other canonical formal module')
for name, digest in candidate['source_sha256'].items():
    if name.startswith('native/ports/formal_worker/'):
        require(sha(Path(prior['source']) / name) == digest, 'unchanged native worker')
build, compiler = read(E / 'managed-build-result.json'), read(E / 'produced-compiler.json')
require(build['id'] == candidate['managed_handle'] and build['status'] == 'succeeded'
        and build['exit_code'] == 0 and build['spawn_count'] == 1, 'one successful managed SDK production')
require(compiler['status'] == 'passed' and compiler['sdk'] == pin['sdk'] and compiler['files'] == 141
        and compiler['manifest_sha256'] == read(P / 'evidence/session-lifetime/produced-compiler.json')['manifest_sha256'],
        'same complete P/B/C-qualified compiler floor')
preflight = read(E / 'source-preflight.json')
require(preflight['beam-selection']['modality'] == 'proven' and not any(preflight[k] for k in
        ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')), 'Source preflight')
baseline = read(E / 'baseline-source-pin.json')
require(baseline['sdk_pin'] == prior and '0 passed, 5 failed' in (E / 'baseline-checks.txt').read_text(), 'real red baseline')
for name, digest in baseline['source_sha256'].items():
    committed(baseline['code_commit'], name, digest)
first = (E / 'focused-checks.txt').read_text()
require(first == (E / 'focused-1-test-assumption.txt').read_text()
        and '1594 passed, 1 failed' in first and '13 file(s) passed, 1 failed, 0 incoherent' in first,
        'initial native/interface run, including its retained test-assumption failure')
focused = counts(E / 'focused-checks.txt')
fixed = counts(E / 'focused-temporal-checks.txt')
require(fixed == {'system.formal-temporal-test': 1595}
        and '1 file(s) passed, 0 failed, 0 incoherent' in (E / 'focused-temporal-checks.txt').read_text(),
        'targeted corrected test passes on same SDK')
require(len(focused) == 13 and 'system.formal-temporal-test' not in focused, 'all other focused files passed unchanged')
focused.update(fixed)
require(len(focused) == 14 and sum(focused.values()) == 2373, 'combined focused coverage across two actual invocations')
regression = counts(E / 'regression-checks.txt')
require(len(regression) == 22 and sum(regression.values()) == 7086
        and '22 file(s) passed, 0 failed, 0 incoherent' in (E / 'regression-checks.txt').read_text(), 'full formal regression')
for name in ('focused-command.json', 'focused-temporal-command.json', 'regression-command.json', 'examples-command.json'):
    cmd = read(E / name)
    require(str(sdk / 'bin/bl') in cmd, 'actual selected SDK command')
    for variable in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH'):
        require(any(cmd[i:i+2] == ['-u', variable] for i in range(len(cmd)-1)), 'unconfigured artifact selection')
total = 0
for name in ('advanced', 'features', 'native'):
    now = read(E / 'regression' / (name + '.json'))
    old = {row['id']: row for row in read(P / 'evidence/session-lifetime/regression' / (name + '.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'healthy paired matrix')
    require(old.keys() == {row['id'] for row in now['cases']}, 'same paired question set')
    for row in now['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete typed question')
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')),
                    'unchanged native capability: ' + row['id'])
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'actual candidate matrix SDK')
    total += len(now['cases'])
require(total == 187, 'all paired native questions')
example = read(E / 'examples.json')
require(example['research-import-path'] is False and not Path(example['cwd']).is_relative_to(R)
        and '-p' not in read(E / 'examples-command.json'), 'ordinary SDK-only program in unrelated cwd')
rows = example['native']
require([row['backend'] for row in rows] == ['z3', 'oxiz'], 'both temporal engines')
require(rows[0]['question-identities'] == rows[1]['question-identities']
        and rows[0]['chronology-question'] == rows[1]['chronology-question'], 'same exact temporal questions')
for row in rows:
    require(row['overlap'] == 'possible' and row['replay'] == ['valid', 'valid']
            and row['consistent'] and row['certificate'] == 'not-checked'
            and row['artifacts']['worker']['origin'] == 'sdk', 'actual default native temporal examples')
require(len(example['laws']) == 3 and all(row['certificate'] == 'checked' for row in example['laws']), 'three portable law certificates')
packets = read(E / 'law-packets.json')
require(len(packets['rows']) == 3 and all(row['data-connection'] == 'checked-data-connection' for row in packets['rows']),
        'three original-term connections')
for row in packets['rows']:
    packet = read(E / (row['id'] + '.json'))
    proof = read(E / 'law-execution' / row['id'] / 'result.json')
    require(packet['identity'] == row['packet'] == proof['packet'] and proof['status'] == 'checked-term-entailment',
            'actual original-term law proof: ' + row['id'])
    require(not proof['compiler_proof_authority'], 'no compiler authority')
    target = E / 'law-execution' / row['id']
    require(sha(target / 'Check.lean') == proof['proof_source_sha256']
            and sha(target / 'Check.olean') == proof['proof_olean_sha256'], 'retained actual proof bytes')
    require(proof['axioms']['originalQuestionEntails'] == ['propext', 'Quot.sound']
            and 'sorryAx' not in (target / 'lean.txt').read_text(), 'checked choice-free theorem dependencies')
prior_proofs = read(E / 'prior-term-proofs/accepted.json')
prior_rejected = read(E / 'prior-term-proofs/rejected.json')
require(len(prior_proofs) == 17 and len(prior_rejected) == 5
        and 'Ran 4 tests' in (E / 'prior-term-proof-checks.txt').read_text()
        and '\nOK\n' in (E / 'prior-term-proof-checks.txt').read_text(), 'real original proof and adversarial regression')
for row in prior_proofs:
    target = E / 'prior-term-proofs' / row['id']
    require(row['status'] == 'checked-term-entailment' and sha(target / 'Check.lean') == row['proof_source_sha256']
            and sha(target / 'Check.olean') == row['proof_olean_sha256'], 'retained prior checked proof')
for row in prior_rejected:
    target = E / 'prior-term-proofs/rejected' / row['id']
    require(row['status'] == 'rejected-by-lean' and not (target / 'Check.olean').exists()
            and (target / 'lean.txt').is_file(), 'changed original cannot retain compiled success')
require(not read(E / 'law-lean-1-note.json')['lean_accepted']
        and not (E / 'law-execution-initial/intersection-symmetry/Check.olean').exists(), 'initial proof search safely refused')
models = [read(P / 'metatheory' / name) for name in ('terms-pin.json', 'refutation-pin.json')]
for model in models:
    require(all(sha(P / model[k]['path']) == model[k]['sha256'] for k in ('source', 'compiled')), 'unchanged pinned model/kernel')
tool = read(P / 'metatheory/tool-pin.json')
require(sha(Path(tool['path']) / 'bin/lean') == tool['binary_sha256'], 'actual pinned Lean executable')
for name in ('TEMPORAL.md', 'temporal-check.bl', 'temporal-laws-export.bl', 'temporal-laws-check.py',
             'term_refutation.py', 'term_refutation_test.py', 'refutation_kernel.py', 'qualify-temporal.py'):
    qualified[str((P / name).relative_to(R))] = sha(P / name)
report = {'schema': 'enchant.formal.temporal-qualification.v1', 'checkpoint': 34, 'sdk_pin': pin,
    'source': {'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(), 'sha256': qualified},
    'managed_build': build, 'compiler': compiler,
    'checks': {'focused': focused, 'focused_invocations': 2, 'regression': regression, 'total_assertions': 9459, 'failed': 0},
    'retained_initial_test_failure': {'passed': 1594, 'failed': 1, 'correction': corrected},
    'baseline': baseline, 'unchanged_paired_questions': total, 'temporal_examples': example,
    'original_term_laws': packets['rows'], 'lean_regression': {'accepted': 17, 'rejected': 5, 'tests': 4},
    'model_pins': models, 'lean_tool': tool,
    'scope': ['semantic integer spans and thirteen Allen relation constructors', 'two complete overlap SAT questions',
              'replayed intersecting/separated assignments', 'strict chronology with full event identities',
              'SDK and selected Source consumers', 'three exact original-term law theorems'],
    'remaining': ['temporal constructor/BL runtime preservation theorem', 'calendar, timezone and recurrence interpretation',
                  'remaining legacy/source Oracle consumers', 'bounded pool admission and formal effect contracts',
                  'language-wide totality and compiler/runtime preservation'], 'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'checkpoint': 34, 'focused': 2373, 'regression': 7086, 'paired_questions': 187, 'original_term_laws': 3}))
