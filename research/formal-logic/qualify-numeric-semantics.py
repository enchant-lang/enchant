"""Audit the numeric candidate's actual gates before any project selection."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_sources(source):
    differences = {}
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest, name
        if sha(R / name) != digest:
            # The fixture repair changes only orchestration. The earlier gates
            # retain their actual committed runner and exact command below.
            assert name == 'research/formal-logic/run-numeric-checks.py', name
            differences[name] = {'recorded': digest, 'current': sha(R / name)}
    return differences


pin = read(E / 'sdk-candidate.json')
baseline = read(E / 'baseline/sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline, 'Qualify before selecting the candidate.'
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
link = read(E / 'build-linkage.json')
assert link['status'] == 'bound' and link['sdk_pin'] == pin
assert link['qualified_baseline'] == baseline
assert len(link['source_sha256']) == 714 and len(link['source_changes']) == 8
metadata = read(Path(pin['sdk']) / 'artifact.json')
for name, digest in link['source_sha256'].items():
    assert sha(R / name) == sha(Path(pin['source']) / name) == digest, name
    assert sha(Path(metadata['source']) / name) == digest, name
    assert sha(Path(pin['sdk']) / 'lib/beam_lisp-0.1.0' / name) == digest, name
floor = read(E / 'compiler-floor-install.json')
assert floor['status'] == 'passed' and len(floor['after']) == 141
for name, digest in floor['after'].items():
    assert sha(R / 'priv/bootstrap/seed' / name) == digest
    assert sha(Path(metadata['compiler']) / 'seed' / name) == digest
    assert sha(Path(pin['sdk']) / 'image/priv/bootstrap/seed' / name) == digest

stages = {}
for stage in ('compiler-floor', 'preflight', 'preflight-controls', 'js-unit',
              'focused', 'datom', 'managed', 'regression', 'native'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    changed_runners = checked_sources(source)
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired'], stage
    command = read(E / (stage + '-command.json'))
    cap = '2G' if stage == 'js-unit' else '4G'
    ceiling = 120 if stage == 'js-unit' else (3600 if stage == 'native' else 900)
    assert all(flag in command for flag in ('--property=MemoryMax=' + cap,
        '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=' + str(ceiling),
        '--property=KillMode=control-group', '--expand-environment=no'))
    assert all(flag in command for flag in ('BEAM_LISP_PATH', 'ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY'))
    if stage in ('focused', 'datom', 'managed', 'regression', 'native'):
        assert pin['sdk'] + '/bin/bl' in command and '--cold' in command
        assert ('-p' in command) == (stage in ('regression', 'native'))
    stages[stage] = {'source_pin': source, 'exit': result,
        'changed_historical_runner': changed_runners,
        'command_sha256': sha(E / (stage + '-command.json')),
        'log_sha256': sha(E / (stage + '-checks.txt'))}

compiler = read(E / 'produced-compiler.json')
assert compiler['status'] == 'passed' and compiler['files'] == 141 and compiler['generations'] == 3
assert compiler['sdk'] == pin['sdk'] and compiler['sdk_descriptor_sha256'] == pin['descriptor_sha256']
assert compiler['compiler'] == metadata['compiler']
preflight = read(E / 'source-preflight.json')
assert preflight['root'] == pin['source'] and preflight['runtime'] == pin['sdk']
assert preflight['selected-count'] == 595
for name in ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis'):
    assert preflight[name] == 0
assert 'SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text()
jslog = (E / 'js-unit-checks.txt').read_text()
assert re.search(r'# tests 40\b', jslog) and re.search(r'# pass 40\b', jslog)
assert re.search(r'# fail 0\b', jslog) and re.search(r'# skipped 0\b', jslog)
runs = {}
for stage, files in (('focused', 7), ('datom', 3), ('managed', 5), ('regression', 31)):
    log = (E / (stage + '-checks.txt')).read_text()
    rows = {name: int(count) for name, count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
    assert len(rows) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in log, stage
    runs[stage] = rows
assert runs['focused']['numeric.equality-test'] == 2479
assert sum(runs['managed'].values()) == 952
assert sum(runs['regression'].values()) == 8141

C = E / 'candidate'
summary = read(C / 'observation-summary.json')
assert summary['sdk_pin'] == pin and summary['mode'] == 'candidate'
assert summary['differences'] == {'beam': 0, 'js-direct': 0, 'js-compiled': 0}
checked_sources(summary['source_pin'])
assert all(read(C / 'retirement.json').values())
observations = {}
for stage in ('beam', 'js-direct', 'js-build', 'js-compiled'):
    source = read(C / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    checked_sources(source)
    assert read(C / (stage + '-exit.json'))['exit_code'] == 0
for target in ('beam', 'js-direct', 'js-compiled'):
    report = read(C / (target + '.json'))
    assert sha(C / (target + '.json')) == summary['reports_sha256'][target]
    assert report['values'] == 30 and report['pairs'] == len(report['rows']) == 900
    assert not report['differences'] and all(row['matches-exact-profile'] for row in report['rows'])
    assert report['managed-query-calls'] == 0 and report['compiler-proof-authority'] is False
    assert len(report['named-float-approximations']) == 11
    observations[target] = report
approximation_values = lambda report: [(row['id'], row['value']) for row in report['named-float-approximations']]
assert approximation_values(observations['beam']) == approximation_values(observations['js-direct']) == approximation_values(observations['js-compiled'])
assert all(row['matches-beam'] for target in ('js-direct', 'js-compiled')
           for row in observations[target]['named-float-approximations'])
compiled = observations['js-compiled']
assert len(compiled['representation-samples']) == 5
assert len(compiled['decimal-oracle']['rows']) == 1051 and not compiled['decimal-oracle']['differences']
assert all(row['expected'] == row['actual'] for row in compiled['decimal-oracle']['rows'])
assert sha(C / 'compiled-manifest.json') == summary['compiled_manifest_sha256']
assert sha(C / 'compiled.tar.gz') == summary['compiled_archive_sha256']
manifest = read(C / 'compiled-manifest.json')
with tarfile.open(C / 'compiled.tar.gz') as archive:
    actual = {str(Path(member.name).relative_to('compiled')): hashlib.sha256(archive.extractfile(member).read()).hexdigest()
              for member in archive.getmembers() if member.isfile()}
assert actual == manifest
assert manifest['rt.mjs'] == link['source_sha256']['priv/lib/js/rt.mjs']

native = read(E / 'native.json')
oldnative = read(P / 'evidence/managed-graph/paired-native-corpus.json')
assert native['compiler-proof-authority'] is False and len(native['rows']) == 187
before = {row['id']: row for row in oldnative['rows']}
assert set(before) == {row['id'] for row in native['rows']}
differences = []
for row in native['rows']:
    old = before[row['id']]
    assert row['roots'] == old['roots'] and row['standard-identity'] == old['standard-identity']
    for engine in ('z3', 'oxiz'):
        new, prior = row[engine], old[engine]
        assert new['identity']['sdk'] == pin['sdk'] and new['identity']['backend'] == engine
        for key in ('worker-sha256', 'library-sha256'):
            assert new['identity'][key] == prior['identity'][key]
        for key in ('solver-status', 'verdict', 'phase', 'observation-basis'):
            if new.get(key) != prior.get(key):
                differences.append({'id': row['id'], 'backend': engine, 'field': key,
                                    'before': prior.get(key), 'after': new.get(key)})
        if new['validation'].get('status') != prior['validation'].get('status'):
            differences.append({'id': row['id'], 'backend': engine, 'field': 'validation.status',
                'before': prior['validation'].get('status'), 'after': new['validation'].get('status')})
(E / 'native-differences.json').write_text(json.dumps(differences, indent=2) + '\n')
assert not differences, differences
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
report = {'schema': 'bl.numeric-semantics-qualification.v1', 'status': 'passed',
    'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
    'baseline_sdk_pin': baseline, 'stages': stages, 'runs': runs,
    'build_linkage_sha256': sha(E / 'build-linkage.json'),
    'observation_summary_sha256': sha(C / 'observation-summary.json'),
    'native_sha256': sha(E / 'native.json'), 'native_differences': differences,
    'finite_values': 30, 'ordered_pairs_per_target': 900, 'targets': 3,
    'compiled_decimal_oracle_cases': 1051, 'compiled_representation_cases': 5,
    'named_float_approximation_cases_per_target': 11, 'compiler_floor_files': 141,
    'paired_native_questions': 187, 'project_pin_selected': False,
    'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
    'compiler_proof_authority': False,
    'scope': 'Finite exact numeric equality/order, named compiled JS Decimal operations, captured oracle values/raisedness, host ABI, Datom scale/index behavior, managed/project regressions and unchanged paired native outcomes on one immutable SDK. Raw map/set key relations remain separate. No whole-target correspondence, exception/effect equivalence, verified compiler or language totality theorem.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'sdk': pin['sdk'], 'assertion_executions': sum(sum(rows.values()) for rows in runs.values()),
                  'compiled_decimal_cases': 1051, 'paired_native_questions': 187, 'project_pin_selected': False}))
