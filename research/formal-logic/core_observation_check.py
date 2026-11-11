"""Check the recorded prefixes of one owned actor observation in the exact Core."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import core_actor_check as actor
import core_term_check as core
from core_composition import compile_module
from obligation_proof import data_digest, digest
import term_refutation as terms

k, require = terms.k, terms.require
MODULE = 'CoreObservedTrace'
OBSERVATION_PROFILES = {
    'bl/source-record-handlers-v1': 'bl/owned-beam-observation-v1',
    'bl/context-record-handlers-v2': 'bl/context-beam-observation-v2',
}
FIELDS = {'formal/core-actor-observation-data', 'profile', 'identity-profile', 'identity', 'model', 'observation', 'frames'}
INPUTS = """
def recordedInputs (integers : List Int) (booleans : List Bool) : Inputs :=
  ⟨fun n => integers[n]?.getD 0, fun n => booleans[n]?.getD false⟩

def projectedFailure : Option String := some "zero-divisor"
"""


class ObservationDecoder(core.Decoder):
    def __init__(self, text):
        self.tokens = re.findall(r'[A-Za-z][A-Za-z0-9.]*|[0-9]+|[()\[\],]', text)
        require(''.join(self.tokens) == re.sub(r'\s+', '', text), 'unknown generated observation token')
        self.at = 0


def canonical_identity(packet):
    observation = packet['observation']
    data = {**packet, 'profile': k.Keyword(packet['profile']), 'identity-profile': k.Keyword(packet['identity-profile']),
            'model': actor.typed_model(packet['model']),
            'observation': {**observation, **{field: k.Keyword(observation[field]) for field in ('profile', 'adapter', 'projection')}},
            'frames': [{**frame, 'kind': k.Keyword(frame['kind']), 'invariant': k.Keyword(frame['invariant']),
                        **({'error': k.Keyword(frame['error'])} if 'error' in frame else {})} for frame in packet['frames']]}
    del data['identity']
    return data_digest(data)


def check_record(sort, value):
    for kind, item, _ in core.payload_leaves(sort, value):
        require(type(item) is (int if kind == 'int' else bool), 'observed scalar value has exact sort')


def validate(packet):
    require(type(packet) is dict and set(packet) == FIELDS, 'Core observation packet fields')
    require(type(packet['formal/core-actor-observation-data']) is int and packet['formal/core-actor-observation-data'] == 1
            and packet['profile'] == 'bl/core-actor-observation-data-v1'
            and packet['identity-profile'] == 'bl/canonical-formal-data-v1', 'Core observation packet profile')
    digest(packet['identity'], 'Core observation packet')
    model = packet['model']
    layouts = actor.validate_model(model)
    observation = packet['observation']
    require(type(observation) is dict and set(observation) == {'receipt', 'profile', 'adapter', 'projection', 'sdk-descriptor', 'artifacts'}
            and observation['profile'] == OBSERVATION_PROFILES[model['subject']['source-profile']]
            and observation['adapter'] == 'sequential-trap-and-stop-v1'
            and observation['projection'] == 'bl/integer-bif-error-projection-v1', 'owned observation projection profile')
    digest(observation['receipt'], 'recorded receipt')
    digest(observation['sdk-descriptor'], 'recorded SDK descriptor')
    manifest = model['subject']['handlers']
    artifacts = observation['artifacts']
    require(type(artifacts) is list and len(artifacts) == len(manifest), 'exact observation artifact coverage')
    modules = set()
    for row, handler in zip(artifacts, manifest):
        require(type(row) is list and len(row) == 4 and row[:2] == handler, 'exact observation artifact handler')
        module = row[2]
        require(type(module) is str and re.fullmatch(r'Elixir\.Formal\.Observed\.M[0-9]{1,24}\.H([0-9]|1[0-5])', module)
                and module not in modules, 'owned observation module slot')
        modules.add(module)
        digest(row[3], 'recorded BEAM bytes')
    by_name = {row['name']: row['core']['inputs'][0][1] for row in model['handlers']}
    frames = packet['frames']
    require(type(frames) is list and 1 <= len(frames) <= 65, 'recorded prefix capacity')
    for index, frame in enumerate(frames):
        require(type(frame) is dict and {'kind', 'state', 'invariant'} <= set(frame), 'recorded frame shape')
        tag = frame['kind']
        require(tag == 'initial' if index == 0 else tag in ('idle', 'returned', 'raised'), 'recorded frame kind at prefix')
        require(frame['invariant'] in ('holds', 'violated', 'incomplete'), 'recorded invariant classification')
        check_record(model['state-sort'], frame['state'])
        extra = set(frame) - {'kind', 'state', 'invariant'}
        if tag in ('initial', 'idle'):
            require(not extra, 'initial and idle frames contain only state and invariant')
        else:
            require(extra == ({'handler', 'message', 'error'} if tag == 'raised' else {'handler', 'message'}),
                    'exact recorded handler frame fields')
            require(type(frame['handler']) is str and frame['handler'] in by_name, 'recorded handler belongs to exact manifest')
            check_record(by_name[frame['handler']], frame['message'])
            if tag == 'raised':
                require(frame['error'] == 'zero-divisor', 'only the named integer BIF projection is admitted')
    require(canonical_identity(packet) == packet['identity'], 'canonical Core observation packet identity mismatch')
    return layouts


def concrete_state(sort, fields):
    values = dict(fields)
    return core.product(sort, lambda name, child: core.int_data(values[name]) if child == ['int'] else values[name],
                        'Prod.mk', 'Unit.unit')


def concrete_message(layout, frame):
    root = core.component('core', '.input/', 'message')
    values = {core.component(root, '/field/', name): value for name, value in frame['message']}
    integers = [core.int_data(values.get(name, 0)) for name in layout[0]]
    booleans = [values.get(name, False) for name in layout[1]]
    return ('recordedInputs', integers, booleans)


def model_declarations(model, layouts):
    symbols, state_layout, handler_layouts = layouts
    rows = actor.state_definitions(model, symbols, state_layout)
    for index, (handler, layout) in enumerate(zip(model['handlers'], handler_layouts)):
        rows.append((f'admission{index} : Term FormalTerms.Ty.boolean', handler['admission'], layout))
    return rows


def concrete_declarations(packet, layouts):
    model = packet['model']
    sort = model['state-sort']
    state = core.render(core.core_sort(sort))
    by_name = {row['name']: index for index, row in enumerate(model['handlers'])}
    rows = []
    failure = 'none'
    for n, frame in enumerate(packet['frames']):
        tag = frame['kind']
        if tag == 'raised':
            failure = 'projectedFailure'
        if n:
            event = 'none'
            if tag != 'idle':
                index = by_name[frame['handler']]
                rows.extend([(f'recordedHandler{n} : Fin handlers.length', ('Fin.mk', index, ('by', 'decide')), None),
                             (f'recordedMessage{n} : Inputs', concrete_message(layouts[2][index], frame), None)])
                event = ('some', ('Prod.mk', f'recordedHandler{n}', f'recordedMessage{n}'))
            rows.append((f'recordedEvent{n} : Event handlers', event, None))
        configuration = ('Prod.mk', concrete_state(sort, frame['state']), failure)
        rows.append((f'recordedConfig{n} : Configuration {state}', configuration, None))
    count = len(packet['frames'])
    rows.extend([('recordedEvents : List (Event handlers)', [f'recordedEvent{n}' for n in range(1, count)], None),
                 (f'recordedConfigurations : List (Configuration {state})', [f'recordedConfig{n}' for n in range(count)], None)])
    return rows


def model_sections(model, layouts):
    groups = []
    for index, (row, layout) in enumerate(zip(model['handlers'], layouts[2])):
        declarations = [(name, data, None) for name, data in core.sections(row['core'], *layout)[:2]]
        groups.append((f'ActorHandlerCore{index}', declarations))
    return groups


def model_boundary(packet):
    model = packet['model']
    state = core.render(core.core_sort(model['state-sort']))
    count = len(model['handlers'])
    tail = '\n\ndef policy := StatePolicy.mk stateSlots stateIntCount stateBoolCount initialPredicate invariantPredicate\n'
    tail += ''.join(actor.CORE_HANDLER.format(n=n, state=state) for n in range(count))
    handlers = ', '.join(f'handler{n}' for n in range(count))
    tail += f'\n\ndef handlers : List (Handler {state}) := [{handlers}]\n'
    return tail, {f'handler{n}ReadsState' for n in range(count)}


def trace_boundary(packet, safety):
    audits = set()
    text = []
    failure_at, violation_at = None, None
    for n, frame in enumerate(packet['frames']):
        kind = frame['kind']
        if n:
            if kind == 'idle':
                step = f'Step.idle recordedConfig{n-1}'
            else:
                step = f'Step.{kind} recordedHandler{n} recordedMessage{n} (by rfl) (by rfl)'
            name = f'recordedStep{n}'
            text.append(f'theorem {name} : Step handlers recordedConfig{n-1} recordedEvent{n} recordedConfig{n} :=\n  {step}')
            audits.add(name)
        name = f'recordedPrefix{n}'
        at = f'(recordedConfigurations.get ⟨{n}, by decide⟩)'
        proof = f'Trace.append recordedPrefix{n-1} recordedStep{n}' if n else 'Trace.start (by rfl)'
        text.append(f'theorem {name} : Trace handlers policy.initial (recordedEvents.take {n}) {at} :=\n  {proof}')
        audits.add(name)
        if kind == 'raised' and failure_at is None:
            failure_at = n
        claim = frame['invariant']
        if claim != 'incomplete':
            name = f'recordedInvariant{n}'
            polarity = '¬ ' if claim == 'violated' else ''
            proof = 'by\n  unfold StatePolicy.invariant holds\n  decide' if polarity else 'rfl'
            text.append(f'theorem {name} : {polarity}policy.invariant {at}.1 := {proof}')
            audits.add(name)
            if polarity and violation_at is None:
                violation_at = n
        if safety or (failure_at is None and claim == 'holds'):
            name = f'recordedSafe{n}'
            proof = f'originalHandlerTracesSafe recordedPrefix{n}' if safety else f'⟨recordedInvariant{n}, rfl⟩'
            text.append(f'theorem {name} : policy.invariant {at}.1 ∧ {at}.2 = none :=\n  {proof}')
            audits.add(name)
    verdict = 'safe'
    if failure_at is not None or violation_at is not None:
        n = min(i for i in (failure_at, violation_at) if i is not None)
        at = f'(recordedConfigurations.get ⟨{n}, by decide⟩)'
        proof = 'by\n  intro safe\n  cases safe.2' if n == failure_at else f'fun safe => recordedInvariant{n} safe.1'
        text.append(f'theorem recordedUnsafePrefix : ¬ (policy.invariant {at}.1 ∧ {at}.2 = none) :=\n  {proof}')
        audits.add('recordedUnsafePrefix')
        verdict = 'unsafe'
    elif not safety and any(frame['invariant'] == 'incomplete' for frame in packet['frames']):
        verdict = 'incomplete'
    return '\n\n' + '\n\n'.join(text) + '\n\n', audits, verdict, failure_at, violation_at


def sections(packet, layouts, safety):
    model = packet['model']
    header = ('import CoreActorCheck\n' if safety else 'import ActorTrace\n') + actor.HEADER + f'\nnamespace {MODULE}\n'
    groups = [] if safety else model_sections(model, layouts)
    definitions = [] if safety else model_declarations(model, layouts)
    model_tail, model_audits = ('', set()) if safety else model_boundary(packet)
    tail, audits, verdict, failed, violated = trace_boundary(packet, safety)
    audits |= model_audits
    tail += f'end {MODULE}\n\n'
    tail += ''.join(f'#print axioms {MODULE}.{name}\n' for name in sorted(audits))
    return header, groups, definitions, model_tail + INPUTS, tail, {f'{MODULE}.{name}' for name in audits}, verdict, failed, violated


def source(packet, layouts, safety):
    header, groups, definitions, model_tail, tail, *_ = sections(packet, layouts, safety)
    programs = ''.join(f'\nnamespace {namespace}\n' + actor.emit_definitions(rows) + f'\nend {namespace}\n'
                       for namespace, rows in groups)
    return (header + programs + actor.emit_definitions(definitions) + model_tail
            + actor.emit_definitions(concrete_declarations(packet, layouts)) + tail)


def verify_source(text, packet, layouts, safety):
    header, groups, definitions, model_tail, tail, audits, verdict, failed, violated = sections(packet, layouts, safety)
    require(text.startswith(header) and text.endswith(tail), 'exact observation model and trace template')
    text = text[len(header):-len(tail)]
    for namespace, rows in groups:
        opening = f'\nnamespace {namespace}\n'
        require(text.startswith(opening), 'exact observed Core program namespace')
        body, boundary, text = text[len(opening):].partition(f'\nend {namespace}\n')
        require(boundary, 'closed observed Core program')
        actor.verify_definitions(body, rows)
    model, boundary, concrete = text.partition(model_tail)
    require(boundary, 'exact observed Core policy template')
    if definitions:
        actor.verify_definitions(model, definitions)
    else:
        require(not model, 'no imported model overrides')
    actor.verify_definitions(concrete, concrete_declarations(packet, layouts), decoder_class=ObservationDecoder)
    return audits, verdict, failed, violated


def run(path, output, axiom_policy='lean-standard', *, safety_path=None):
    require(axiom_policy in terms.AXIOM_POLICIES, 'supported observation axiom policy')
    output.mkdir(parents=True, exist_ok=True)
    for filename in (MODULE + '.olean', 'result.json', 'lean.txt'):
        (output / filename).unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'Core observation packet byte capacity')
    packet = k.load_packet(path)
    layouts = validate(packet)
    safety = None
    if safety_path is not None:
        require(safety_path.stat().st_size <= k.MAX_BYTES, 'Core actor safety packet byte capacity')
        safety = k.load_packet(safety_path)
        actor.validate(safety)
        require(actor.model_data(safety) == packet['model'], 'all-traces proof is for a different exact actor model')
    text = source(packet, layouts, safety is not None)
    audits, verdict, failed, violated = verify_source(text, packet, layouts, safety is not None)
    lean, libraries = actor.checked_kernel()
    linked = None
    with tempfile.TemporaryDirectory(prefix='enchant-observed-trace-') as temporary:
        work = Path(temporary)
        library = work / 'library'
        core.copy_library(library, libraries)
        if safety is not None:
            # Use the already parsed and matched bytes, even if the supplied file changes.
            pinned = work / 'safety.json'
            pinned.write_text(json.dumps(safety))
            safety_output = output / 'safety'
            linked = actor.run(pinned, safety_output, axiom_policy)
            for filename, key in [('CoreActorCheck.olean', 'olean_sha256'),
                                  ('premises/ActorPremises.olean', 'imported_olean_sha256')]:
                file = safety_output / filename
                target = library / file.name
                shutil.copyfile(file, target)
                require(k.sha(target) == linked[key], 'fresh exact safety theorem import')
        dependencies = compile_module(work, library, output, module=MODULE, text=text, lean=lean, axiom_policy=axiom_policy,
                                      expected_audits=audits, failure='Lean did not accept the exact recorded Core trace')
    result = {'schema': 'enchant.formal.core-actor-observation-execution.v1', 'status': 'checked-recorded-core-trace',
              'scope': 'one-finite-recorded-execution-of-the-contained-core-handlers',
              'packet': packet['identity'], 'subject': packet['model']['subject'], 'observation': packet['observation'],
              'events': len(packet['frames']) - 1, 'checked_prefixes': len(packet['frames']),
              'recorded_safety': verdict, 'first_failure_at': failed, 'first_invariant_violation_at': violated,
              'all_traces_safety_packet': safety['identity'] if safety else None,
              'all_traces_olean_sha256': linked['olean_sha256'] if linked else None,
              'source_sha256': k.sha(output / (MODULE + '.lean')), 'olean_sha256': k.sha(output / (MODULE + '.olean')),
              'axioms': dependencies, 'axiom_policy': axiom_policy,
              'receipt_connection': 'requires-fresh-BL-reconstruction', 'execution_authenticity': 'observer-trusted',
              'universal_runtime_refinement': 'not-established', 'compiler_proof_authority': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--safety', type=Path)
    parser.add_argument('--axiom-policy', choices=sorted(terms.AXIOM_POLICIES), default='lean-standard')
    args = parser.parse_args()
    try:
        result = run(args.packet, args.output, args.axiom_policy, safety_path=args.safety)
        print(json.dumps({key: result[key] for key in ('status', 'packet', 'checked_prefixes', 'recorded_safety', 'all_traces_safety_packet')}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError, TypeError, KeyError) as error:
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
