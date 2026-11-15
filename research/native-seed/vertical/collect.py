#!/usr/bin/env python3
"""Collect the closed reader experiment and project observed model histories.

This data adapter does not authenticate native events or establish generation
custody. Source-model replay independently checks its explicit projections.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def identity(path):
    return {'path': str(path.resolve()),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--beam', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('choose a new observation directory')
    capture_path = args.native / 'proof.json'
    runtime_path = args.native / 'native-observation/runtime.json'
    log_path = args.native / 'native-observation/runtime.log'
    beam_path = args.beam / 'receipt.json'
    cleanup_path = args.beam / 'cleanup.json'
    capture, runtime, beam, cleanup = map(read, [capture_path, runtime_path, beam_path, cleanup_path])
    assert capture['prototype'] == 'reader-ignored-char-v1'
    assert runtime['passed'] and runtime['exit'] == 0
    assert not runtime['runtime-admission'] and not runtime['generation-custody']
    assert beam['reader-forms-equal'] and beam['setup-compile-source-calls'] == 2
    assert cleanup['context-restored'] and all(row.get('retired') is True for row in cleanup['results'])
    assert beam['scalar-proof']['sha256'] == capture['scalar-gate']['receipt']['sha256']
    timings, events = {}, []
    log = log_path.read_text()
    for line in log.splitlines():
        if line.startswith('VERTICAL_READER_TIMING\t'):
            _, phase, revision, batch, repetitions, seconds = line.split('\t')
            timings.setdefault(phase, []).append(float(seconds) / int(repetitions))
        if line.startswith('VERTICAL_NATIVE_EVENT '):
            events.append(json.loads(line.removeprefix('VERTICAL_NATIVE_EVENT ')))
    assert 'VERTICAL_READER_CHECKS 77\nNATIVE_VERTICAL_READER_PASS\n' in log
    beam_timings = {}
    for row in beam['timings']:
        assert row['compile-source-calls'] == 0
        beam_timings.setdefault(row['phase'], []).append(row['seconds'] / row['repetitions'])
    phases = {'helper-original', 'helper-candidate', 'read-original', 'read-candidate'}
    assert set(timings) == set(beam_timings) == phases
    assert all(len(rows) == 5 for rows in [*timings.values(), *beam_timings.values()])
    medians = {backend: {phase: statistics.median(rows) for phase, rows in values.items()}
               for backend, values in [('native', timings), ('beam-private-aot', beam_timings)]}
    ratios = {backend: {phase: values[phase + '-original'] / values[phase + '-candidate']
                       for phase in ['helper', 'read']} for backend, values in medians.items()}
    versions = capture['versions']
    first, second = (row['provider']['selection_key'] for row in versions)
    assert [(event['event'], event['revision']) for event in events] == [
        ('publish', 1), ('request-accepted', 1), ('request-reference-fallback', 1),
        ('request-reference-fallback', 1), ('candidate-request', 2), ('fail', 2),
        ('publish', 2), ('request-accepted', 0), ('request-accepted', 2), ('held-old-after-gc', 1)]
    assert all(row['selection'] == (first if row['revision'] == 1 else second) for row in events)
    assert len({row['image'] for row in events}) == len({row['kernel'] for row in events}) == 1
    phase_rows = {row['label']: row for row in capture['phases']}
    for label in ['unchanged-warm-workspace-and-artifacts', 'unchanged-v2-warm-workspace-and-artifacts']:
        assert all(phase_rows[label][key] == 0 for key in ['compiler-jobs', 'emissions', 'stage-calls'])
    assert phase_rows['old-provider-prepared-refused']['compiler-jobs'] == 0
    assert capture['planner']['stale-consumer'] == 'artifact-source-changed'
    assert capture['planner']['consumer-source-unchanged'] and capture['planner']['consumer-plan-stable']
    assert not capture['planner']['consumer-artifact-reused']
    # States below are projections from explicit observations, not snapshots of
    # a native reload.generation implementation. No retirement event is inferred.
    cache0 = dict(source=1, compiler=1, abi=1, **{
        'cached-source': 1, 'cached-compiler': 1, 'cached-abi': 1, 'ready': True, 'hit': False})
    cache_edit = {**cache0, 'source': 2, 'ready': False}
    cache_done = {**cache_edit, 'cached-source': 2, 'ready': True}
    publication0 = dict(current=1, published=1, previous=1, ready=True, failed=False, admitted=False)
    publication_edit = {**publication0, 'current': 2, 'ready': False}
    publication_fail = {**publication_edit, 'failed': True}
    receipts = {name: identity(path) for name, path in [
        ('native-preparation', capture_path), ('native-runtime', runtime_path), ('native-log', log_path),
        ('beam-runtime', beam_path), ('beam-cleanup', cleanup_path)]}
    def event(name, inputs=None):
        return {'transition': name, 'inputs': inputs or {}}
    observations = {
        'schema': 'bl.native.vertical-history-observations', 'version': 1,
        'identity_mapping': {
            'source': {'1': versions[0]['provider']['fixture'], '2': versions[1]['provider']['fixture']},
            'compiler': {'1': capture['sdk']},
            'abi': {'1': {'image': events[0]['image'], 'kernel': events[0]['kernel']}},
            'revision': {'1': first, '2': second},
            'meaning': 'finite labels for these exact receipts; labels do not confer authority'},
        'artifact_receipts': receipts,
        'histories': [
            {'id': 'actual-unchanged-artifacts', 'family': 'cache', 'initial': cache0,
             'events': [event('reuse')], 'states': [cache0, {**cache0, 'hit': True}],
             'raw_events': [phase_rows['unchanged-warm-workspace-and-artifacts']],
             'projection': 'hit means verified unchanged artifacts with zero stage/emission/C jobs; latency remains measured separately'},
            {'id': 'actual-edit-stale-refusal-completion-reuse', 'family': 'cache', 'initial': cache0,
             'events': [event('edit', dict(source=2, compiler=1, abi=1)),
                        event('complete', dict(source=1, compiler=1, abi=1)),
                        event('complete', dict(source=2, compiler=1, abi=1)), event('reuse')],
             'states': [cache0, cache_edit, cache_edit, cache_done, {**cache_done, 'hit': True}],
             'raw_events': [phase_rows[key] for key in ['old-provider-prepared-refused',
                            'emit-provider-v2', 'unchanged-v2-warm-workspace-and-artifacts']],
             'projection': 'producer filesystem Source/prepared-world history; distinct from the later native live-serving history'},
            {'id': 'actual-pre-init-failure-keeps-serving', 'family': 'publication', 'initial': publication0,
             'events': [event('edit', {'revision': 2}), event('fail')],
             'states': [publication0, publication_edit, publication_fail],
             'raw_events': events[4:6],
             'projection': 'candidate request and refused malformed pre-init load; native check asserts the exact serving registry root is unchanged'},
        ],
        'scope': 'explicit observation-to-model projection; no native controller or custody proof',
        'native_retirement_observed': False, 'native_lowering_proof': False,
        'compiler_proof_authority': False,
    }
    comparison = {
        'schema': 'bl.native.vertical-reader-comparison', 'version': 1,
        'status': 'helper-improves-whole-reader-unchanged', 'product_qualification': False,
        'native_checks': 77, 'beam_differential_cases': beam['differential-cases'],
        'median_seconds': medians, 'reference_over_candidate': ratios,
        'samples_seconds_per_operation': {'native': timings, 'beam-private-aot': beam_timings},
        'native_unchanged_v1_seconds': phase_rows['unchanged-warm-workspace-and-artifacts']['microseconds'] / 1e6,
        'native_unchanged_v2_seconds': phase_rows['unchanged-v2-warm-workspace-and-artifacts']['microseconds'] / 1e6,
        'native_stage_emission_c_jobs_on_unchanged': 0,
        'whole_compiler_speed_gate': 'still-failing; unchanged earlier 35.01x diagnostic',
        'limits': ['five interleaved batches are a scoped diagnostic, not a statistical speed qualification',
                   'helper batches use different outer observer loops; compare reference/candidate within each backend',
                   'BEAM runs privately AOT-derived namespaces with owned Env entry; this differs from the earlier SDK global baseline',
                   'whole-reader rows execute the same six-form Source three times; startup/setup/proof/build excluded',
                   'candidate Int branch is checked separately; runtime observations do not prove Gambit/C lowering'],
        'artifact_receipts': receipts,
    }
    args.out.mkdir(parents=True)
    for name, value in [('histories.json', observations), ('comparison.json', comparison)]:
        (args.out / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'comparison': str(args.out / 'comparison.json'),
                      'histories': str(args.out / 'histories.json'), 'ratios': ratios}))


if __name__ == '__main__':
    main()
