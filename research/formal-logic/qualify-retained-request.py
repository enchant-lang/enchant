"""Audit the exact artifact and every required gate before a separate selection step."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/retained-request'
C = P / 'evidence/numeric-semantics'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin, baseline = read(E / 'sdk-candidate.json'), read(E / 'baseline-sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
assert read(C / 'qualification.json')['status'] == 'passed' and read(C / 'qualification.json')['sdk_pin'] == baseline
sdk = Path(pin['sdk'])
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
metadata = read(sdk / 'artifact.json')
linkage = read(E / 'build-linkage.json')
assert linkage['status'] == 'bound' and linkage['sdk_pin'] == pin and linkage['qualified_baseline'] == baseline
assert len(linkage['source_sha256']) == 716 and len(linkage['source_changes']) == 7
for name, digest in linkage['source_sha256'].items():
    assert sha(R / name) == sha(Path(pin['source']) / name) == sha(Path(metadata['source']) / name) == sha(sdk / 'lib/beam_lisp-0.1.0' / name) == digest
assert linkage['unchanged_components'] == {name: metadata[name] for name in ('platform', 'formalWorker')}
old_metadata = read(Path(baseline['sdk']) / 'artifact.json')
assert all(old_metadata[name] == metadata[name] for name in ('platform', 'formalWorker'))
floor_path = C / 'compiler-floor-install.json'
floor = read(floor_path)
assert floor['status'] == 'passed' and len(floor['after']) == linkage['compiler_floor_files'] == 141
assert sha(floor_path) == linkage['compiler_floor_install_sha256']
for name, digest in floor['after'].items():
    assert sha(R / 'priv/bootstrap/seed' / name) == sha(Path(metadata['compiler']) / 'seed' / name) == sha(sdk / 'image/priv/bootstrap/seed' / name) == digest
# Numeric and JS behavior is inherited by exact unchanged implementation
# bytes, with the predecessor qualification retained explicitly as evidence.
numeric_names = ['priv/boot/rt.bl', 'priv/host/num.bl', 'priv/host/decimal.bl', 'priv/lib/decimal.bl',
                 'priv/lib/system/smt.bl', 'priv/lib/js/rt.mjs', 'priv/lib/js/leaves.mjs', 'priv/lib/js/host-leaves.mjs']
for name in numeric_names:
    assert sha(Path(baseline['source']) / name) == linkage['source_sha256'][name]
stages = {}
runs = {}
for stage in ('preflight', 'preflight-controls', 'focused', 'legacy', 'regression', 'native'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        assert sha(R / name) == digest, name
        assert hashlib.sha256(subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired'], stage
    command = read(E / (stage + '-command.json'))
    assert all(flag in command for flag in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + ('3600' if stage == 'native' else '1200'), '--property=KillMode=control-group'))
    log = (E / (stage + '-checks.txt')).read_text()
    if stage in ('focused', 'legacy', 'regression', 'native'):
        assert pin['sdk'] + '/bin/bl' in command and '--cold' in command
        assert ('-p' in command) == (stage in ('regression', 'native'))
    if stage in ('focused', 'legacy', 'regression'):
        count = {'focused': 7, 'legacy': 5, 'regression': 31}[stage]
        rows = {name: int(total) for name, total in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
        assert len(rows) == count and f'{count} file(s) passed, 0 failed, 0 incoherent' in log
        assert result['complete_green_test_summary'] is True
        runs[stage] = rows
    stages[stage] = {'source_pin': source, 'exit': result, 'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
assert sum(runs['focused'].values()) == 569 and runs['focused']['formal.retained-request-check'] == 90
assert sum(runs['legacy'].values()) == 818
assert sum(runs['regression'].values()) == 8141
preflight = read(E / 'source-preflight.json')
assert preflight['root'] == pin['source'] and preflight['runtime'] == pin['sdk'] and preflight['selected-count'] == 597
for name in ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis'):
    assert preflight[name] == []
assert preflight['selector_changed_during_analysis'] is False and preflight['driver_changed_during_analysis'] is False
assert 'SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text()
records = read(E / 'records-qualification.json')
assert records['status'] == 'passed' and records['sdk_pin'] == pin
assert records['records'] == records['ledger_rows_per_reader'] == records['refusal_controls'] == 12
assert records['fresh_sdk_only_readers'] == 2 and records['solver_exchanges'] == records['oracle_calls'] == 0
assert read(E / 'corpus-ledger-retirement.json')['retired'] is True
previous = read(E / 'previous-readers-qualification.json')
assert previous['status'] == 'passed' and previous['sdk_pin'] == pin
assert previous['questions'] == 187 and previous['replayed_points_per_reader'] == 52
assert previous['fresh_sdk_only_readers'] == 2 and previous['refusal_controls'] == 11 and previous['solver_exchanges'] == 0
native = read(E / 'native.json')
before = {row['id']: row for row in read(C / 'native.json')['rows']}
assert native['compiler-proof-authority'] is False and len(native['rows']) == 187
assert set(before) == {row['id'] for row in native['rows']}
differences = []
for row in native['rows']:
    old = before[row['id']]
    assert row['roots'] == old['roots'] and row['standard-identity'] == old['standard-identity']
    for engine in ('z3', 'oxiz'):
        current, prior = row[engine], old[engine]
        assert current['identity']['sdk'] == pin['sdk'] and current['identity']['backend'] == engine
        for key in ('worker-sha256', 'library-sha256'):
            assert current['identity'][key] == prior['identity'][key]
        for key in ('solver-status', 'verdict', 'phase', 'observation-basis'):
            if current.get(key) != prior.get(key):
                differences.append({'id': row['id'], 'backend': engine, 'field': key, 'before': prior.get(key), 'after': current.get(key)})
        if current['validation'].get('status') != prior['validation'].get('status'):
            differences.append({'id': row['id'], 'backend': engine, 'field': 'validation.status',
                                'before': prior['validation'].get('status'), 'after': current['validation'].get('status')})
(E / 'native-differences.json').write_text(json.dumps(differences, indent=2) + '\n')
assert not differences, differences
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
report = {'schema': 'bl.retained-request-sdk-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'baseline_sdk_pin': baseline,
          'build_linkage_sha256': sha(E / 'build-linkage.json'), 'source_changes': linkage['source_changes'],
          'inherited_numeric_qualification_sha256': sha(C / 'qualification.json'), 'unchanged_numeric_source_sha256': {name: linkage['source_sha256'][name] for name in numeric_names},
          'inherited_compiler_floor_install_sha256': sha(floor_path), 'compiler_floor_files': 141,
          'stages': stages, 'assertion_runs': runs, 'beam_assertions': sum(sum(rows.values()) for rows in runs.values()),
          'preflight_namespaces': 597, 'records_qualification_sha256': sha(E / 'records-qualification.json'),
          'previous_records_qualification_sha256': sha(E / 'previous-readers-qualification.json'),
          'native_questions': 187, 'native_outcome_differences': differences, 'native_sha256': sha(E / 'native.json'),
          'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'project_pin_selected': False, 'compiler_proof_authority': False,
          'scope': 'One immutable retained-request SDK: graph-native composition, atomic owner settings, versioned portable answers, nested leases, canonical/legacy/project regressions, actual durable records and fresh solver-denied readers, previous record compatibility and unchanged paired native outcomes. Numeric implementation bytes and the compiler floor inherit explicit preceding qualifications. No general native-history authentication, complete theory coverage, compiler preservation or language totality theorem is established.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'beam_assertions': report['beam_assertions'], 'native_questions': 187, 'project_pin_selected': False}))
