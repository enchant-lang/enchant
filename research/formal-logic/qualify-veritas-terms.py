"""Bind Veritas term, replay and durable-record checks to one immutable SDK."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/veritas-terms'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require(ok, reason):
    if not ok:
        raise AssertionError(reason)


def counts(name, files):
    text = (E / name).read_text()
    result = {n: int(c) for n, c in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    require(len(result) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in text,
            'complete successful check: ' + name)
    return result


pin, snapshot = read(E / 'sdk-candidate.json'), read(E / 'sdk-source-pin.json')
sdk, source = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
require(pin == snapshot['sdk_pin'], 'same implementation SDK')
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'] and meta['source'] == str(source), 'descriptor and source')
production = read(E / 'preparation-result.json')
require(production['ok'] is True and production['value']['kind'] == 'preparation-result'
        and production['value']['output'] == pin['sdk'] and production['value']['operation'] == 'sdk', 'managed SDK production receipt')
for name, digest in snapshot['source_sha256'].items():
    require(sha(R / name) == digest, 'unchanged implementation: ' + name)
    require(hashlib.sha256(subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest,
            'committed implementation: ' + name)
    if name.startswith('priv/'):
        require(sha(source / name) == digest, 'actual immutable SDK source: ' + name)
checked = read(E / 'check-source-pin.json')
for name, digest in checked['source_sha256'].items():
    if name == 'test/bl/doc_nested_spans_test.bl':
        committed = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)
        require(hashlib.sha256(committed).hexdigest() == digest and sha(E / 'checked-doc-nested-spans-test.bl') == digest,
                'actual SDK-era Org regression program; later independent parser changes are outside this qualification')
    else:
        require(sha(R / name) == digest, 'checked program: ' + name)
        committed = subprocess.check_output(['git', 'show', checked['code_commit'] + ':' + name], cwd=R)
        require(hashlib.sha256(committed).hexdigest() == digest, 'committed check program: ' + name)
for name, digest in snapshot.get('incidental_sdk_source_sha256', {}).items():
    require(sha(source / name) == digest, 'incidental SDK source: ' + name)
prior = read(E / 'baseline-sdk-pin.json')
previous = read(Path(prior['sdk']) / 'artifact.json')
require(meta['formalWorker'] == previous['formalWorker'], 'unchanged native worker')
for path in (R / 'priv/lib/formal').glob('*.bl'):
    old = Path(prior['source']) / path.relative_to(R)
    if old.exists() and path.name not in ('source.bl', 'intrinsics.bl'):
        require(sha(path) == sha(old), 'unchanged preceding formal module: ' + path.name)
floor, preflight = (read(E / n) for n in ('produced-compiler.json', 'source-preflight.json'))
require(floor['status'] == 'passed' and floor['sdk'] == pin['sdk'] and floor['files'] == 141, 'complete produced compiler floor')
require(preflight['beam-selection']['modality'] == 'exhausted' and preflight['beam-selection']['complete'] is True
        and preflight['declaration-cases']['modality'] == 'exhausted' and not any(preflight[k] for k in
        ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')), 'source preflight')
require(preflight['root'] == str(source) and preflight['runtime'] == str(sdk)
        and preflight['selector_sha256'] == sha(source / 'priv/build/sdk-source-selection.bl')
        and preflight['driver_sha256'] == sha(R / 'scripts/sdk-preflight.bl'), 'actual preflight source and reader')
require('SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text(), 'preflight refusal controls')
require('0 passed, 6 failed, 1 errored' in (E / 'baseline-checks.txt').read_text(), 'retained previous-SDK failures')
require('not green' in (E / 'focused-1-checks.txt').read_text() and 'not green' in (E / 'regression-checks.txt').read_text(),
        'retained initial test and downstream failures')
require('veritas.model-serve-test  56 passed' in (E / 'http-baseline-checks.txt').read_text()
        and 'veritas.model-serve-test  56 passed' in (E / 'http-isolated-checks.txt').read_text(), 'retained isolated HTTP comparisons')
focused, regression = counts('focused-current-checks.txt', 15), counts('regression-current-checks.txt', 31)
require(focused['veritas.term-queries-test'] == 181 and regression['veritas.ledger-test'] >= 28, 'new meaningful interface and ledger checks')
paired = 0
for name in ('advanced', 'features', 'native'):
    now = read(E / 'regression-current' / (name + '.json'))
    old = {x['id']: x for x in read(P / 'evidence/source-properties/regression' / (name + '.json'))['cases']}
    require(not now['disagreements'] and not now['invalid-models'], 'paired matrix healthy')
    require(old.keys() == {x['id'] for x in now['cases']}, 'same paired questions')
    for row in now['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete question')
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')), 'same native capability')
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'matrix SDK provenance')
    paired += len(now['cases'])
require(paired == 187, '187 preceding paired questions')
for name in ('focused-current-command.json', 'regression-current-command.json', 'examples-command.json', 'ledger-write-command.json', 'ledger-read-command.json'):
    command = read(E / name)
    require(str(sdk / 'bin/bl') in command, 'exact SDK command: ' + name)
    for var in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH'):
        require(any(command[i:i+2] == ['-u', var] for i in range(len(command)-1)), 'default SDK artifacts')
example = read(E / 'examples.json')
require(example['research-import-path'] is False and not Path(example['cwd']).is_relative_to(R)
        and '-p' not in read(E / 'examples-command.json'), 'SDK-only use from unrelated cwd')
require(example['units'] == {'graphemes': 1, 'codepoints': 2}, 'actual runtime text units')
engines = example['native']
require([r['backend'] for r in engines] == ['z3', 'oxiz'], 'both native backends')
expected = {'mixed-product': 'solver-claim', 'false-enum-payload': 'witnessed', 'empty-pop': 'refuted',
            'rest-kind': 'solver-claim', 'clause-coverage': 'solver-claim', 'coverage-gap': 'refuted', 'large-candidate': 'candidate'}
for engine in engines:
    rows = {r['id']: r for r in engine['rows']}
    require(all(rows[k]['modality'] == v for k, v in expected.items()), 'SDK-only result meanings')
    require(rows['unicode-prefix']['modality'] == ('solver-claim' if engine['backend'] == 'z3' else 'unknown'), 'honest Unicode capability difference')
    require(rows['false-enum-payload']['witness'] == {'left/open': False}, 'complete enum identity and false payload')
    for name in ('false-enum-payload', 'empty-pop', 'coverage-gap'):
        require(rows[name]['term-replay'] == 'valid' and rows[name]['runtime-replay'] == 'reproduced', 'term and actual predicate replay')
require([r['question'] for r in engines[0]['rows']] == [r['question'] for r in engines[1]['rows']], 'same new questions across backends')
runtime = example['runtime-search']
require(runtime['nil-present'] and runtime['nil-witness'] is None and runtime['false-witness'] is False
        and runtime['sample-absence'] == 'unknown' and runtime['sample-none'] is not True, 'runtime witness presence and absence')
write, reread = read(E / 'ledger-write.json'), read(E / 'ledger-read.json')
require(write['mode'] == 'write' and reread['mode'] == 'read' and write['rows'] == reread['rows'] == 3
        and write['process'] != reread['process'], 'fresh-process durable question and nil/false roundtrip')
report = {'schema': 'enchant.formal.veritas-terms-qualification.v1', 'checkpoint': 36, 'sdk_pin': pin,
          'source': {'code_commit': snapshot['code_commit'], 'sha256': snapshot['source_sha256']},
          'incidental_sdk_source': snapshot.get('incidental_sdk_source_sha256', {}),
          'incidental_scope': snapshot.get('incidental_scope'),
          'focused': focused, 'regression': regression, 'bl_assertions': sum(focused.values()) + sum(regression.values()),
          'paired_questions': paired, 'sdk_only': True, 'durable_ledger_fresh_process': True,
          'unicode_prefix': {'z3': 'solver-claim', 'oxiz': 'unknown'}, 'compiler_proof_authority': False,
          'compiler_changed_since_previous': meta['compiler'] != previous['compiler'],
          'http_admission_history': {'initial_batch': 'one unexpected log entry; cause unresolved',
              'previous_sdk_isolated': '56 assertions passed', 'candidate_2_isolated': '56 assertions passed',
              'current_full_batch': '57 assertions passed with admission diagnostics'},
          'evidence_sha256': {n: sha(E / n) for n in ('focused-current-checks.txt', 'regression-current-checks.txt',
              'examples.json', 'ledger-write.json', 'ledger-read.json', 'produced-compiler.json', 'source-preflight.json')}}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'checkpoint': 36, 'assertions': report['bl_assertions'], 'paired_questions': paired}))
