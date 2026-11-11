"""Check every finite admitted trace of the contained source-handler Core programs."""
import argparse
import json
from pathlib import Path
import subprocess

import core_loop_check as loops
import core_term_check as core
from core_composition import check_linked
from obligation_proof import data_digest, digest, typed_term_packet
import term_refutation as terms

P, k, require = terms.P, terms.k, terms.require
HEADER = """
set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
set_option linter.unusedSimpArgs false
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop ActorTrace
"""
POLICY = """

def policy := StatePolicy.mk stateSlots stateIntCount stateBoolCount initialPredicate invariantPredicate
theorem invariantReadsStateOnly : replace policy.mask policy.inv = policy.inv := rfl

theorem stateSlotsCovered : policy.covered := by
  intro value left right
  apply inputs_ext
"""
INIT = """
theorem exactInitialQuestion :
    renameQuestion ActorInitTerms.originalQuestion (fun n => initialIntSlots[n]?.getD 0)
      (fun n => initialBoolSlots[n]?.getD 0) = policy.initQuestion := rfl

theorem initialStatesAreSafe : ∀ value, policy.initial value → policy.invariant value :=
  checked_init policy (exactInitialQuestion ▸ rename_entails ActorInitTerms.originalQuestion _ _
    ActorInitTerms.originalQuestionEntails)
"""
HANDLER = """

def handlerEnv{n} (input : Inputs) := ActorHandlerCore{n}.originalInputs input.ints input.bools
def handler{n} := coreHandler policy ActorHandlerCore{n}.originalProgram handlerEnv{n} admission{n}

theorem handler{n}ReadsState (value : Value {state}) (message : Inputs) :
    (handlerEnv{n} (stateSlots.put value message)).lookup (Var.succ Var.zero) = value := rfl

theorem exactHandler{n}Question :
    renameQuestion ActorHandlerTerms{n}.originalQuestion (fun i => handler{n}IntSlots[i]?.getD 0)
      (fun i => handler{n}BoolSlots[i]?.getD 0) =
      policy.handlerQuestion admission{n} ActorHandlerCore{n}.symbolicOK ActorHandlerCore{n}.symbolicValue := rfl

theorem handler{n}Safe : Safe handler{n} policy.invariant :=
  checked_handler policy stateSlotsCovered invariantReadsStateOnly
    ActorHandlerCore{n}.originalProgram handlerEnv{n} admission{n} ActorHandlerCore{n}.symbolicOK
    ActorHandlerCore{n}.symbolicValue ActorHandlerCore{n}.symbolicError (errorCode ActorHandlerCore{n}.errorCodes)
    (fun input => ActorHandlerCore{n}.coreTermCorrespondence input.ints input.bools)
    (exactHandler{n}Question ▸ rename_entails ActorHandlerTerms{n}.originalQuestion _ _
      ActorHandlerTerms{n}.originalQuestionEntails)
"""


def canonical_identity(packet):
    subject = packet['subject']
    data = {**packet, 'profile': k.Keyword(packet['profile']), 'identity-profile': k.Keyword(packet['identity-profile']),
            'subject': {**subject, 'kind': k.Keyword(subject['kind']), 'source-profile': k.Keyword(subject['source-profile'])},
            'state-sort': core.typed_sort(packet['state-sort']),
            'initial': terms.typed_term(packet['initial']), 'invariant': terms.typed_term(packet['invariant']),
            'initial-proof': typed_term_packet(packet['initial-proof']),
            'handlers': [{**row, 'core': core.typed_packet(row['core']), 'admission': terms.typed_term(row['admission']),
                          'entailment': typed_term_packet(row['entailment'])} for row in packet['handlers']]}
    del data['identity']
    return data_digest(data)


def state_symbols(sort):
    core.validate_sort(sort)
    require(core.record(sort) and all(field_sort in core.SCALARS for _, field_sort in sort[1]),
            'source protocol state is a closed scalar record')
    root = core.component('core', '.input/', 'state')
    return {field: (field_sort[0], core.component(root, '/field/', field)) for field, field_sort in sort[1]}


def typed_roots(roots, allowed, label):
    names = terms.validate_roots(roots)
    require(all(allowed.get(name) == sort for name, sort in names.items()), label + ' typed input scope')


def slot_maps(proof, question, layout):
    used = terms.validate(proof)
    require(proof['normalized']['question'] == question and all(set(subset) <= set(full) for subset, full in zip(used, layout)),
            'exact question identity and named proof slots')
    return [[full.index(name) for name in subset] for subset, full in zip(used, layout)]


def validate(packet):
    require(type(packet) is dict and set(packet) == {'formal/core-actor-data', 'profile', 'identity-profile', 'identity',
            'subject', 'state-sort', 'initial', 'invariant', 'initial-question', 'initial-proof', 'handlers'},
            'Core actor packet fields')
    require(type(packet['formal/core-actor-data']) is int and packet['formal/core-actor-data'] == 1
            and packet['profile'] == 'bl/core-actor-trace-data-v1'
            and packet['identity-profile'] == 'bl/canonical-formal-data-v1', 'Core actor packet profile')
    digest(packet['identity'], 'Core actor packet')
    subject = packet['subject']
    require(type(subject) is dict and set(subject) == {'kind', 'identity', 'model', 'source-profile', 'handlers'}
            and subject['kind'] == 'source-protocol'
            and subject['source-profile'] in ['bl/source-record-handlers-v1', 'bl/context-record-handlers-v2'],
            'exact source protocol subject')
    for field in ('identity', 'model'):
        digest(subject[field], field)
    digest(packet['initial-question'], 'initiation question')
    symbols = state_symbols(packet['state-sort'])
    state_names = {name: sort for sort, name in symbols.values()}
    state_layout = tuple(sorted(name for name, sort in state_names.items() if sort == kind) for kind in ('int', 'bool'))
    typed_roots([packet['initial'], packet['invariant']], state_names, 'state predicates')
    initial_maps = slot_maps(packet['initial-proof'], packet['initial-question'], state_layout)
    handlers = packet['handlers']
    require(type(handlers) is list and len(handlers) <= 16, 'source handler capacity')
    mappings, manifest, labels = [], [], set()
    for row in handlers:
        require(type(row) is dict and set(row) == {'name', 'admission', 'core', 'question', 'entailment'}
                and core.name_ok(row['name']) and row['name'] not in labels, 'unique exact handler row')
        labels.add(row['name'])
        digest(row['question'], 'handler question')
        model = row['core']
        layout = core.validate(model)
        require(model['subject']['kind'] == 'core' and model['prefix'] == 'core' and model['input-encoding'] == 'record-paths-v2'
                and model['body']['sort'] == packet['state-sort'], 'exact handler result state')
        require(len(model['inputs']) == 2 and [entry[0] for entry in model['inputs']] == ['message', 'state']
                and model['inputs'][1][1] == packet['state-sort'], 'exact state and message record inputs')
        message_sort = model['inputs'][0][1]
        require(core.record(message_sort) and all(field_sort in core.SCALARS for _, field_sort in message_sort[1]),
                'closed scalar message record')
        require(all(all_names[:len(state)] == state for all_names, state in zip(layout, state_layout)),
                'the state slots must be shared before the message slots')
        typed_roots([row['admission']], {name: kind for names, kind in zip(layout, ('int', 'bool')) for name in names}, 'message admission')
        mappings.append((layout, slot_maps(row['entailment'], row['question'], layout)))
        manifest.append([row['name'], model['core']])
    require(subject['handlers'] == manifest, 'complete ordered handler manifest')
    require(canonical_identity(packet) == packet['identity'], 'canonical Core actor packet identity mismatch')
    return symbols, state_layout, initial_maps, mappings


def definitions(packet, layouts):
    symbols, state_layout, initial_maps, mappings = layouts
    slots = 'Layout.unit'
    for _, (sort, name) in reversed(list(symbols.items())):
        slot = state_layout[0 if sort == 'int' else 1].index(name)
        slots = ('Layout.pair', ('Layout.' + sort, slot), slots)
    rows = [('stateSlots', slots, None), ('stateIntCount : Nat', len(state_layout[0]), None),
            ('stateBoolCount : Nat', len(state_layout[1]), None),
            ('initialPredicate : Term FormalTerms.Ty.boolean', packet['initial'], state_layout),
            ('invariantPredicate : Term FormalTerms.Ty.boolean', packet['invariant'], state_layout),
            ('initialIntSlots : List Nat', initial_maps[0], None), ('initialBoolSlots : List Nat', initial_maps[1], None)]
    for index, (handler, (layout, maps)) in enumerate(zip(packet['handlers'], mappings)):
        rows.extend([(f'admission{index} : Term FormalTerms.Ty.boolean', handler['admission'], layout),
                     (f'handler{index}IntSlots : List Nat', maps[0], None),
                     (f'handler{index}BoolSlots : List Nat', maps[1], None)])
    return rows


def coverage_cases(count):
    lines = ['  · intro n']
    indent = '    '
    for _ in range(count):
        lines.extend([indent + 'cases n with', indent + '| zero => rfl', indent + '| succ n =>'])
        indent += '  '
    lines.append(indent + 'simp [StatePolicy.erase, policy, stateIntCount, stateBoolCount, Nat.succ_lt_succ_iff]')
    return '\n'.join(lines) + '\n'


def boundaries(packet, layouts):
    n = len(packet['handlers'])
    modules = ['ActorTrace', 'ActorInitTerms']
    for i in range(n):
        modules.extend([f'ActorHandlerCore{i}', f'ActorHandlerTerms{i}'])
    header = ''.join('import ' + module + '\n' for module in modules) + HEADER
    state = core.render(core.core_sort(packet['state-sort']))
    tail = POLICY + ''.join(coverage_cases(len(names)) for names in layouts[1]) + INIT
    tail += ''.join(HANDLER.format(n=i, state=state) for i in range(n))
    handlers = ', '.join(f'handler{i}' for i in range(n))
    tail += f'\n\ndef handlers : List (Handler {state}) := [{handlers}]\n\n'
    tail += 'theorem allHandlersSafe : ∀ handler ∈ handlers, Safe handler policy.invariant := by\n  intro handler member\n'
    tail += '  simp only [handlers, List.mem_cons, List.not_mem_nil, or_false] at member\n'
    if n == 1:
        tail += '  subst handler\n  exact handler0Safe\n'
    elif n > 1:
        tail += '  rcases member with ' + ' | '.join(f'h{i}' for i in range(n)) + '\n'
        tail += ''.join(f'  · subst handler; exact handler{i}Safe\n' for i in range(n))
    tail += f"""
theorem originalHandlerTracesSafe {{events : List (Event handlers)}} {{final : Configuration {state}}}
    (trace : Trace handlers policy.initial events final) :
    policy.invariant final.1 ∧ final.2 = none :=
  trace_safe handlers policy.initial policy.invariant initialStatesAreSafe allHandlersSafe trace

theorem failureRetainsState {{before : Value {state}}} {{reason : String}} {{event : Event handlers}}
    {{after : Configuration {state}}}
    (transition : Step handlers (before, some reason) event after) :
    event = none ∧ after = (before, some reason) :=
  after_failure handlers transition

"""
    audits = ['stateSlotsCovered', 'invariantReadsStateOnly', 'exactInitialQuestion', 'initialStatesAreSafe',
              'allHandlersSafe', 'originalHandlerTracesSafe', 'failureRetainsState']
    for i in range(n):
        audits.extend([f'handler{i}ReadsState', f'exactHandler{i}Question', f'handler{i}Safe'])
    return header, tail + ''.join(f'#print axioms {name}\n' for name in audits), set(audits)


def source(packet, layouts):
    header, tail, _ = boundaries(packet, layouts)
    return header + ''.join('\n\ndef ' + name + ' :=\n' +
                            (terms.emit_term(data, *layout) if layout is not None else core.render(data))
                            for name, data, layout in definitions(packet, layouts)) + tail


def verify_source(text, packet, layouts):
    header, tail, audits = boundaries(packet, layouts)
    require(text.startswith(header) and text.endswith(tail), 'fixed Core actor theorem template')
    rows = text[len(header):-len(tail)].split('\n\ndef ')
    require(rows.pop(0) == '', 'Core actor declarations start')
    expected = definitions(packet, layouts)
    require(len(rows) == len(expected), 'exact Core actor declarations')
    for row, (name, data, layout) in zip(rows, expected):
        prefix = name + ' :=\n'
        require(row.startswith(prefix), 'Core actor declaration type')
        decoder = core.Decoder(row[len(prefix):])
        if layout is not None:
            require(terms.faithful(data, decoder.term(), *layout), 'generated actor predicate differs')
        else:
            require(decoder.data() == data, 'generated actor state or proof slots differ')
        require(decoder.at == len(decoder.tokens), 'trailing Core actor declaration data')
    return audits


def checked_kernel():
    lean, libraries = loops.checked_kernel()
    pin = json.loads((P / 'metatheory/actor-trace-pin.json').read_text())
    for key in ('source', 'compiled', 'core_loop'):
        require(k.sha(P / pin[key]['path']) == pin[key]['sha256'], 'Core actor model dependency pin')
    require(json.loads((P / pin['core_loop']['path']).read_text()) == libraries['CoreLoop'], 'exact shared substitution model')
    libraries['ActorTrace'] = pin
    return lean, libraries


def run(path, output, axiom_policy='lean-standard'):
    require(axiom_policy in terms.AXIOM_POLICIES, 'supported Core actor axiom policy')
    output.mkdir(parents=True, exist_ok=True)
    module = 'CoreActorCheck'
    for name in (module + '.olean', 'result.json', 'lean.txt'):
        (output / name).unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'Core actor packet byte capacity')
    packet = k.load_packet(path)
    layouts = validate(packet)
    text = source(packet, layouts)
    audits = verify_source(text, packet, layouts)
    lean, libraries = checked_kernel()
    leaves = {'initial-proof': packet['initial-proof']}
    premises = [('initial-proof', 'ActorInitTerms')]
    for i, row in enumerate(packet['handlers']):
        leaves.update({f'handler-{i}-core': row['core'], f'handler-{i}-entailment': row['entailment']})
        premises.extend([(f'handler-{i}-core', f'ActorHandlerCore{i}'), (f'handler-{i}-entailment', f'ActorHandlerTerms{i}')])
    imported, axioms = check_linked(leaves, text, output, module=module, premises=premises, lean=lean, libraries=libraries,
        axiom_policy=axiom_policy, expected_audits=audits, failure='Lean did not accept the exact Core actor trace composition')
    result = {'schema': 'enchant.formal.core-actor-trace-execution.v1', 'status': 'checked-core-actor-trace-safety',
              'packet': packet['identity'], 'subject': packet['subject'], 'handler_count': len(packet['handlers']),
              'scope': 'all-finite-admitted-traces-of-the-contained-core-handlers', 'trace_bound': None,
              'imported_olean_sha256': imported, 'axioms': axioms, 'axiom_policy': axiom_policy,
              'source_sha256': k.sha(output / (module + '.lean')), 'olean_sha256': k.sha(output / (module + '.olean')),
              'subject_connection': 'requires-fresh-BL-reconstruction', 'initial_feasibility': 'not-checked',
              'live_actor_preservation': 'not-established', 'compiler_proof_authority': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--axiom-policy', choices=sorted(terms.AXIOM_POLICIES), default='lean-standard')
    args = parser.parse_args()
    try:
        result = run(args.packet, args.output, args.axiom_policy)
        print(json.dumps({key: result[key] for key in ('status', 'packet', 'handler_count', 'axioms')}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
