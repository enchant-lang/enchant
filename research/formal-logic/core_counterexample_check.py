"""Connect an original bounded query witness to the same recorded unsafe Core run."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import core_observation_check as observed
import core_term_check as core
from core_composition import compile_module
from obligation_proof import data_digest, digest
import term_refutation as terms
import witness_kernel as witnesses

k, require = terms.k, terms.require
MODULE = 'CoreCounterexampleCheck'
PROFILE = 'bl/core-protocol-counterexample-data-v1'
ORIGINS = {'backend-assignment', 'backend-observation', 'explicit-replay-completion', 'model-execution-completion'}
HEADER = '''import Check
import CoreObservedTrace

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
open BeamLispCore FormalTerms FormalRefutation FormalWitness CoreTerms CoreContract CoreLoop ActorTrace

namespace CoreCounterexampleCheck
'''
QUERY = '''

def originalQuestion : Question := ⟨originalContext.take assumptionCount, originalClaim⟩

theorem originalContextMatches :
    originalContext = originalQuestion.assertions ++ [.not originalQuestion.claim] := rfl

theorem originalAssumptionsHold :
    originalQuestion.assumed suppliedWitness.integerEnv suppliedWitness.booleanEnv := by
  intro assertion member
  apply originalContextHolds assertion
  rw [originalContextMatches]
  exact List.mem_append_left _ member

theorem originalClaimIsFalse :
    originalQuestion.claim.eval suppliedWitness.integerEnv suppliedWitness.booleanEnv = some false := by
  have negative := originalContextHolds (.not originalQuestion.claim) (by
    rw [originalContextMatches]
    exact List.mem_append_right _ (by simp))
  change FormalRefutation.pNot
    (originalQuestion.claim.eval suppliedWitness.integerEnv suppliedWitness.booleanEnv) = some true at negative
  cases result : originalQuestion.claim.eval suppliedWitness.integerEnv suppliedWitness.booleanEnv with
  | none => simp [result, FormalRefutation.pNot] at negative
  | some value =>
    cases value with
    | false => rfl
    | true => simp [result, FormalRefutation.pNot] at negative

theorem originalQueryHasCounterexample :
    ∃ integers booleans, originalQuestion.assumed integers booleans ∧
      originalQuestion.claim.eval integers booleans = some false :=
  ⟨suppliedWitness.integerEnv, suppliedWitness.booleanEnv, originalAssumptionsHold, originalClaimIsFalse⟩
'''


def canonical_identity(packet):
    subject, discovery, layout = (packet[key] for key in ('subject', 'discovery', 'layout'))
    data = {**packet, 'profile': k.Keyword(packet['profile']), 'identity-profile': k.Keyword(packet['identity-profile']),
            'subject': {**subject, 'kind': k.Keyword(subject['kind']), 'profile': k.Keyword(subject['profile'])},
            'discovery': {**discovery, 'engine': k.Keyword(discovery['engine'])},
            'claim': terms.typed_term(packet['claim']), 'witness': witnesses.typed_packet(packet['witness']),
            'bindings': [[name, core.typed_sort(sort), value, k.Keyword(origin), k.Keyword(availability)]
                         for name, sort, value, origin, availability in packet['bindings']],
            'layout': {'states': [[[field, terms.typed_term(term)] for field, term in row] for row in layout['states']],
                       'choices': [terms.typed_term(term) for term in layout['choices']],
                       'inputs': [[[name, [[field, terms.typed_term(term)] for field, term in fields]] for name, fields in row]
                                  for row in layout['inputs']]},
            'execution': observed.typed_packet(packet['execution'])}
    del data['identity']
    return data_digest(data)


def validate(packet):
    require(type(packet) is dict and set(packet) == {'formal/core-counterexample-data', 'profile', 'subject', 'discovery',
            'claim', 'witness', 'bindings', 'layout', 'execution', 'identity-profile', 'identity'}, 'Core counterexample packet fields')
    require(type(packet['formal/core-counterexample-data']) is int and packet['formal/core-counterexample-data'] == 1
            and packet['profile'] == PROFILE and packet['identity-profile'] == 'bl/canonical-formal-data-v1',
            'Core counterexample packet profile')
    digest(packet['identity'], 'Core counterexample')
    observed.validate(packet['execution'])
    subject = packet['subject']
    require(type(subject) is dict and set(subject) == {'kind', 'identity', 'profile', 'protocol', 'depth', 'query'}
            and subject['kind'] == 'protocol-trace' and type(subject['depth']) is int and 0 <= subject['depth'] <= 16,
            'original source bounded trace subject')
    for field in ('identity', 'protocol', 'query'):
        digest(subject[field], field)
    source_subject = packet['execution']['model']['subject']
    require(subject['protocol'] == source_subject['identity']
            and subject['profile'] == {'bl/source-record-handlers-v1': 'bl/source-record-trace-v1',
                                      'bl/context-record-handlers-v2': 'bl/context-record-trace-v2'}[source_subject['source-profile']]
            and len(packet['execution']['frames']) == subject['depth'] + 1, 'exact recorded source, profile and depth')
    discovery = packet['discovery']
    require(type(discovery) is dict and set(discovery) == {'engine', 'backend', 'result'}
            and discovery['engine'] in ('z3', 'oxiz'), 'claimed native discovery provenance')
    for key in ('result', 'backend'):
        digest(discovery[key], 'native ' + key)
    layout = witnesses.validate(packet['witness'])
    witness_variables = terms.validate_roots(packet['witness']['assertions'])
    terms.validate_roots([packet['claim']], ['bool'])
    require(packet['witness']['assertions'] and packet['witness']['assertions'][-1] ==
            {'formal/term': 1, 'sort': ['bool'], 'op': 'not', 'data': None, 'args': [packet['claim']]},
            'original claim must be the exact negated witness goal')
    trace_layout = packet['layout']
    require(type(trace_layout) is dict and set(trace_layout) == {'states', 'choices', 'inputs'}, 'complete bounded trace layout')
    depth = subject['depth']
    require(type(trace_layout['states']) is list and len(trace_layout['states']) == depth + 1
            and type(trace_layout['choices']) is list and len(trace_layout['choices']) == depth
            and type(trace_layout['inputs']) is list and len(trace_layout['inputs']) == depth, 'complete layout extent')
    variables, seen = dict(witness_variables), set()

    def variable(term, kind):
        require(type(term) is dict and term.get('op') == 'var' and term.get('sort') == [kind], 'typed trace layout variable')
        names = terms.validate_roots([term], [kind])
        name = term['data']
        require(len(names) == 1 and name not in seen and variables.get(name, kind) == kind, 'distinct typed projection slot')
        seen.add(name)
        variables[name] = kind

    def record(sort, fields):
        require(type(fields) is list and len(fields) == len(sort[1]), 'complete named trace record')
        for entry, (field, child) in zip(fields, sort[1]):
            require(type(entry) is list and len(entry) == 2 and entry[0] == field, 'exact trace field order')
            variable(entry[1], child[0])

    model = packet['execution']['model']
    for fields in trace_layout['states']:
        record(model['state-sort'], fields)
    for term in trace_layout['choices']:
        variable(term, 'int')
    for row in trace_layout['inputs']:
        require(type(row) is list and len(row) == len(model['handlers']), 'every handler input record per step')
        for entry, handler in zip(row, model['handlers']):
            require(type(entry) is list and len(entry) == 2 and entry[0] == handler['name'], 'exact named handler input layout')
            record(handler['core']['inputs'][0][1], entry[1])
    require(set(witness_variables) <= seen, 'original query variables belong to the bounded trace layout')
    bindings = packet['bindings']
    require(type(bindings) is list and len(bindings) <= 4096, 'completed binding capacity')
    names, bound = [], {}
    for row in bindings:
        require(type(row) is list and len(row) == 5, 'completed binding fields')
        name, sort, value, origin, availability = row
        require(type(name) is str and name in variables and sort == [variables[name]]
                and type(value) is (int if variables[name] == 'int' else bool), 'completed binding name and scalar kind')
        require(origin in ORIGINS and availability in ('concrete', 'unavailable')
                and (origin in ('backend-assignment', 'backend-observation')) == (availability == 'concrete'),
                'explicit completion provenance')
        names.append(name)
        bound[name] = (sort, value)
    require(names == sorted(variables), 'exactly one sorted completed binding per original query and layout variable')
    require(all(bound[name] == (sort, value) for name, sort, value in packet['witness']['bindings']),
            'original SAT witness and trace binding values must agree')
    require(canonical_identity(packet) == packet['identity'], 'canonical Core counterexample packet identity mismatch')
    return layout


def declarations(packet, layout):
    integer_names, boolean_names = layout
    supplied = {name: value for name, _, value, _, _ in packet['bindings']}

    def scalar(term):
        name = term['data']
        names, getter = (integer_names, 'integerEnv') if term['sort'] == ['int'] else (boolean_names, 'booleanEnv')
        if name in names:
            return (f'suppliedWitness.{getter}', names.index(name))
        return core.int_data(supplied[name]) if term['sort'] == ['int'] else supplied[name]

    def record(sort, fields):
        values = dict(fields)
        return core.product(sort, lambda name, _: scalar(values[name]), 'Prod.mk', 'Unit.unit')

    model = packet['execution']['model']
    state = core.render(core.core_sort(model['state-sort']))
    rows = [('originalClaim : Term FormalTerms.Ty.boolean', packet['claim'], layout),
            ('assumptionCount : Nat', len(packet['witness']['assertions']) - 1, None)]
    rows.extend((f'projectedState{n} : Value {state}', record(model['state-sort'], fields), None)
                for n, fields in enumerate(packet['layout']['states']))
    by_name = {row['name']: index for index, row in enumerate(model['handlers'])}
    for n, (term, frame) in enumerate(zip(packet['layout']['choices'], packet['execution']['frames'][1:])):
        rows.append((f'projectedChoice{n} : Int', scalar(term), None))
        if frame['kind'] != 'idle':
            index = by_name[frame['handler']]
            sort = model['handlers'][index]['core']['inputs'][0][1]
            fields = packet['layout']['inputs'][n][index][1]
            rows.append((f'projectedMessage{n+1} : Value ' + core.render(core.core_sort(sort)), record(sort, fields), None))
    return rows


def boundary(packet):
    text = QUERY
    audits = {'originalContextMatches', 'originalAssumptionsHold', 'originalClaimIsFalse', 'originalQueryHasCounterexample'}
    claims, proofs = [], []
    frames = packet['execution']['frames']
    by_name = {row['name']: n for n, row in enumerate(packet['execution']['model']['handlers'])}
    for n, frame in enumerate(frames):
        name = f'projectedState{n}Matches'
        claim = f'projectedState{n} = CoreObservedTrace.recordedConfig{n}.1'
        text += f'\ntheorem {name} : {claim} := rfl\n'
        audits.add(name)
        claims.append(claim)
        proofs.append(name)
        if n:
            choice = 0 if frame['kind'] == 'idle' else 1 + by_name[frame['handler']]
            rows = [(f'projectedChoice{n-1}Matches', f'projectedChoice{n-1} = ' + core.render(core.int_data(choice)))]
            if frame['kind'] != 'idle':
                rows.append((f'projectedMessage{n}Matches', f'projectedMessage{n} = CoreObservedTrace.recordedMessageValue{n}'))
            for name, claim in rows:
                text += f'\ntheorem {name} : {claim} := rfl\n'
                audits.add(name)
                claims.append(claim)
                proofs.append(name)
    # Include the complete named state, selected choice and message connection
    # in the final theorem's premises and proof dependencies.
    text += '\ndef projectionMatches : Prop :=\n  ' + ' ∧\n  '.join([*claims, 'True']) + '\n'
    text += '\ntheorem sameProjection : projectionMatches :=\n  ' + ''.join('⟨' + name + ', ' for name in proofs) + 'True.intro' + '⟩' * len(proofs) + '\n'
    _, _, verdict, failure, violation = observed.trace_boundary(packet['execution'], False)
    require(verdict == 'unsafe', 'an original query counterexample must have a recorded unsafe Core prefix')
    unsafe = min(n for n in (failure, violation) if n is not None)
    final = len(frames) - 1
    text += f'''
theorem originalCounterexampleRuns :
    originalQuestion.assumed suppliedWitness.integerEnv suppliedWitness.booleanEnv ∧
    originalQuestion.claim.eval suppliedWitness.integerEnv suppliedWitness.booleanEnv = some false ∧
    projectionMatches ∧
    Trace CoreObservedTrace.handlers CoreObservedTrace.policy.initial
      CoreObservedTrace.recordedEvents (CoreObservedTrace.recordedConfigurations.get ⟨{final}, by decide⟩) ∧
    ¬ (CoreObservedTrace.policy.invariant (CoreObservedTrace.recordedConfigurations.get ⟨{unsafe}, by decide⟩).1 ∧
       (CoreObservedTrace.recordedConfigurations.get ⟨{unsafe}, by decide⟩).2 = none) :=
  ⟨originalAssumptionsHold, originalClaimIsFalse, sameProjection,
    CoreObservedTrace.recordedPrefix{final}, CoreObservedTrace.recordedUnsafePrefix⟩

end CoreCounterexampleCheck

'''
    audits |= {'sameProjection', 'originalCounterexampleRuns'}
    return text + ''.join(f'#print axioms {MODULE}.{name}\n' for name in sorted(audits)), {f'{MODULE}.{name}' for name in audits}


def source(packet, layout):
    tail, _ = boundary(packet)
    return HEADER + observed.actor.emit_definitions(declarations(packet, layout)) + tail


def verify_source(text, packet, layout):
    tail, audits = boundary(packet)
    require(text.startswith(HEADER) and text.endswith(tail), 'exact original query, projection and trace theorem template')
    observed.actor.verify_definitions(text[len(HEADER):-len(tail)], declarations(packet, layout),
                                     decoder_class=observed.ObservationDecoder)
    return audits


def run(path, output, axiom_policy='choice-free'):
    require(axiom_policy in terms.AXIOM_POLICIES, 'supported Core counterexample axiom policy')
    output.mkdir(parents=True, exist_ok=True)
    for filename in (MODULE + '.olean', 'result.json', 'lean.txt'):
        (output / filename).unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'Core counterexample packet byte capacity')
    packet = k.load_packet(path)
    layout = validate(packet)
    text = source(packet, layout)
    audits = verify_source(text, packet, layout)
    lean, libraries = observed.actor.checked_kernel()
    witness_lean, pins = witnesses.checked_kernel()
    require(lean == witness_lean and libraries['Terms'] == pins[1], 'shared typed term semantics for query and Core trace')
    libraries['Witness'] = pins[2]
    with tempfile.TemporaryDirectory(prefix='enchant-core-counterexample-') as temporary:
        work = Path(temporary)
        library = work / 'library'
        core.copy_library(library, libraries)
        trace_path, witness_path = work / 'trace.json', work / 'witness.json'
        trace_path.write_text(json.dumps(packet['execution']))
        witness_path.write_text(json.dumps(packet['witness']))
        trace = observed.run(trace_path, output / 'trace', axiom_policy)
        witness = witnesses.run(witness_path, output / 'witness')
        for file, expected in [(output / 'trace/CoreObservedTrace.olean', trace['olean_sha256']),
                               (output / 'witness/Check.olean', witness['proof_olean_sha256'])]:
            target = library / file.name
            shutil.copyfile(file, target)
            require(k.sha(target) == expected, 'fresh checked query or trace object import')
        dependencies = compile_module(work, library, output, module=MODULE, text=text, lean=lean,
                                      axiom_policy=axiom_policy, expected_audits=audits,
                                      failure='Lean did not accept the original counterexample and recorded projection')
    result = {'schema': 'enchant.formal.core-counterexample-execution.v1', 'status': 'checked-original-query-and-unsafe-core-run',
              'packet': packet['identity'], 'subject': packet['subject'], 'discovery': packet['discovery'],
              'query_witness': packet['witness']['identity'], 'recorded_trace': packet['execution']['identity'],
              'receipt': packet['execution']['observation']['receipt'], 'events': trace['events'], 'checked_prefixes': trace['checked_prefixes'],
              'first_failure_at': trace['first_failure_at'], 'first_invariant_violation_at': trace['first_invariant_violation_at'],
              'completed_bindings': len(packet['bindings']),
              'extra_observation_bindings': len(packet['bindings']) - len(packet['witness']['bindings']),
              'completion_origins': {origin: sum(row[3] == origin for row in packet['bindings']) for origin in sorted(ORIGINS)},
              'imported_query_olean_sha256': witness['proof_olean_sha256'], 'imported_trace_olean_sha256': trace['olean_sha256'],
              'source_sha256': k.sha(output / (MODULE + '.lean')), 'olean_sha256': k.sha(output / (MODULE + '.olean')),
              'axioms': dependencies, 'axiom_policy': axiom_policy,
              'scope': 'one-original-query-counterexample-and-its-exact-recorded-core-run',
              'query_and_receipt_connection': 'requires-fresh-BL-reconstruction',
              'backend_provenance': 'claimed-engine-response', 'execution_authenticity': 'observer-trusted',
              'general_unrolling_correspondence': 'not-established', 'universal_runtime_refinement': 'not-established',
              'compiler_proof_authority': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--axiom-policy', choices=sorted(terms.AXIOM_POLICIES), default='choice-free')
    args = parser.parse_args()
    try:
        result = run(args.packet, args.output, args.axiom_policy)
        print(json.dumps({key: result[key] for key in ('status', 'packet', 'events', 'checked_prefixes')}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError, TypeError, KeyError) as error:
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
