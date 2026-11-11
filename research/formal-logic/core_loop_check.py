"""Check normal return of an exact ranked Core loop without an iteration bound."""
import argparse
import json
from pathlib import Path
import subprocess

import core_term_check as core
from core_composition import check_linked
from obligation_proof import data_digest, digest, typed_term_packet
import term_refutation as terms

P, k, require = terms.P, terms.k, terms.require
HEADER = """import InitializerCore
import ControllerCore
import EntailmentCheck
import CoreLoop

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract LoopTotal CoreLoop
"""
TAIL = """

def policy := Policy.mk stateSlots resultSlot loopPre loopInv rankFirst rankSecond loopPost
def stepData := StepTerms.unpack ControllerCore.symbolicValue
def loopInputs (input : Inputs) := InitializerCore.originalInputs input.ints input.bools
def mapInt (n : Nat) : Nat := integerSlots[n]?.getD 0
def mapBool (n : Nat) : Nat := booleanSlots[n]?.getD 0

theorem sameLoopInputs : ControllerCore.originalInputs = InitializerCore.originalInputs := rfl

theorem exactStepPayload : stepData.pack = ControllerCore.symbolicValue := rfl

theorem exactLoopQuestion :
    renameQuestion originalQuestion mapInt mapBool =
      policy.question InitializerCore.symbolicOK InitializerCore.symbolicValue ControllerCore.symbolicOK stepData := rfl

theorem originalCoreLoopReturns : ∀ input, policy.pre.eval input.ints input.bools = some true →
    ∃ first last result,
      initial InitializerCore.originalProgram loopInputs policy.stateSlots input = .ok first ∧
      Returns (control ControllerCore.originalProgram loopInputs policy.stateSlots) first last result ∧
      policy.good last ∧ policy.resultHolds last result := by
  apply composed_loop policy InitializerCore.originalProgram ControllerCore.originalProgram loopInputs
    InitializerCore.symbolicOK ControllerCore.symbolicOK InitializerCore.symbolicValue stepData
    InitializerCore.symbolicError ControllerCore.symbolicError
    (errorCode InitializerCore.errorCodes) (errorCode ControllerCore.errorCodes)
  · intro input
    exact InitializerCore.coreTermCorrespondence input.ints input.bools
  · intro input
    simpa only [loopInputs, sameLoopInputs, exactStepPayload] using ControllerCore.coreTermCorrespondence input.ints input.bools
  · exact exactLoopQuestion ▸ rename_entails originalQuestion mapInt mapBool originalQuestionEntails

#print axioms sameLoopInputs
#print axioms exactStepPayload
#print axioms exactLoopQuestion
#print axioms originalCoreLoopReturns
"""
AUDITS = {'sameLoopInputs', 'exactStepPayload', 'exactLoopQuestion', 'originalCoreLoopReturns'}


def typed_control(control):
    tagged = {**control, 'control': k.Keyword(control['control'])}
    for key in ('initial', 'test', 'value'):
        if key in control:
            tagged[key] = core.typed_core(control[key])
    for key in ('values', 'prefix'):
        if key in control:
            tagged[key] = [core.typed_core(value) for value in control[key]]
    for key in ('body', 'then', 'else'):
        if key in control:
            tagged[key] = typed_control(control[key])
    return tagged


def canonical_identity(packet):
    program = packet['program']
    policy = packet['policy']
    typed_program = {**program, 'profile': k.Keyword(program['profile']), 'sort': core.typed_sort(program['sort']),
                     'parameters': [[name, core.typed_sort(sort)] for name, sort in program['parameters']],
                     'state': [{**slot, 'sort': core.typed_sort(slot['sort'])} for slot in program['state']],
                     'initial': [core.typed_core(node) for node in program['initial']],
                     'body': typed_control(program['body'])}
    typed_policy = {name: terms.typed_term(policy[name]) for name in ('requires', 'invariant', 'ensures')}
    typed_policy['rank'] = [terms.typed_term(node) for node in policy['rank']]
    data = {**packet, 'profile': k.Keyword(packet['profile']), 'identity-profile': k.Keyword(packet['identity-profile']),
            'subject': {**packet['subject'], 'kind': k.Keyword('loop')}, 'program': typed_program, 'policy': typed_policy,
            'initializer': core.typed_packet(packet['initializer']), 'controller': core.typed_packet(packet['controller']),
            'entailment': typed_term_packet(packet['entailment'])}
    del data['identity']
    return data_digest(data)


def node(op, sort, args, data=None):
    return {'core/node': 1, 'op': op, 'sort': sort, 'args': args, 'data': data}


def record(fields, args):
    sort = ['record', [[name, value['sort']] for name, value in sorted(zip(fields, args))]]
    return node('record', sort, args, fields)


def literal(sort, value):
    return node('const', sort, [], value)


def default(sort):
    return literal(sort, False if sort == ['bool'] else 0)


def reconstructed_program(program, errors_init, errors_step):
    require(type(program) is dict and set(program) == {'formal/loop-core', 'profile', 'parameters', 'state', 'initial', 'body', 'sort'}
            and type(program['formal/loop-core']) is int and program['formal/loop-core'] == 1
            and program['profile'] == 'bl/tail-loop-int-bool-v1' and program['sort'] in core.SCALARS, 'closed loop control profile')
    parameters, slots = program['parameters'], program['state']
    require(type(parameters) is list and len(parameters) <= 16 and type(slots) is list and len(slots) <= 16, 'loop input and state capacity')
    inputs, state = {}, {}
    for row in parameters:
        require(type(row) is list and len(row) == 2 and core.name_ok(row[0]) and row[1] in core.SCALARS
                and 'input/' + row[0] not in inputs, 'declared loop parameter')
        inputs['input/' + row[0]] = row[1]
    require(list(inputs) == sorted(inputs), 'canonical loop parameter order')
    for slot in slots:
        require(type(slot) is dict and set(slot) == {'name', 'id', 'sort'} and core.name_ok(slot['name'])
                and slot['id'] == 'state/' + slot['name'] and slot['sort'] in core.SCALARS
                and slot['id'] not in state, 'declared loop state slot')
        state[slot['id']] = slot['sort']
    require(type(program['initial']) is list and len(program['initial']) == len(state), 'loop initializer arity')
    visits = 0
    result = program['sort']

    def expression(expr, scope, errors, expected=None):
        require(core.validate_core(expr, scope, errors) == 'bl/core-int-bool-outcomes-v1', 'scalar loop expression')
        require(expected is None or expr['sort'] == expected, 'loop expression sort')
        return expr

    def ordered_state(values, scope, errors):
        require(type(values) is list and len(values) == len(state), 'simultaneous loop state update arity')
        return record(list(state), [expression(value, scope, errors, sort) for value, sort in zip(values, state.values())])

    empty = record(list(state), [default(sort) for sort in state.values()])

    def packed(again, value, next_state):
        return record(['again', 'result', 'state'], [literal(['bool'], again), value, next_state])

    def visit(control, scope, depth=0):
        nonlocal visits
        visits += 1
        require(visits <= 256 and depth <= 64 and type(control) is dict, 'closed loop control capacity')
        op = control.get('control')
        fields = {'return': {'value'}, 'recur': {'values'}, 'if': {'test', 'then', 'else'},
                  'let': {'name', 'initial', 'body'}, 'do': {'prefix', 'body'}}
        require(type(op) is str and op in fields and set(control) == fields[op] | {'control'}, 'exact loop control fields')
        if op == 'return':
            return packed(False, expression(control['value'], scope, errors_step, result), empty)
        if op == 'recur':
            return packed(True, default(result), ordered_state(control['values'], scope, errors_step))
        if op == 'if':
            test = expression(control['test'], scope, errors_step, ['bool'])
            yes, no = (visit(control[side], scope, depth + 1) for side in ('then', 'else'))
            return node('if', yes['sort'], [test, yes, no])
        if op == 'let':
            name = control['name']
            require(core.name_ok(name) and name not in scope, 'fresh loop control binding')
            value = expression(control['initial'], scope, errors_step)
            body = visit(control['body'], {**scope, name: value['sort']}, depth + 1)
            return node('let', body['sort'], [value, body], name)
        prefix = control['prefix']
        require(type(prefix) is list and 0 < len(prefix) <= 4096, 'ordered loop control prefix')
        values = [expression(value, scope, errors_step) for value in prefix]
        body = visit(control['body'], scope, depth + 1)
        return node('do', body['sort'], [*values, body])

    initial = ordered_state(program['initial'], inputs, errors_init)
    return inputs, state, initial, visit(program['body'], {**inputs, **state})


def validate(packet):
    require(type(packet) is dict and set(packet) == {'formal/core-loop-data', 'profile', 'identity-profile',
            'identity', 'subject', 'program', 'policy', 'initializer', 'controller', 'entailment'}, 'Core loop packet fields')
    require(type(packet['formal/core-loop-data']) is int and packet['formal/core-loop-data'] == 1
            and packet['profile'] == 'bl/core-loop-data-v1'
            and packet['identity-profile'] == 'bl/canonical-formal-data-v1', 'Core loop packet profile')
    digest(packet['identity'], 'Core loop packet')
    subject = packet['subject']
    require(type(subject) is dict and set(subject) == {'kind', 'identity', 'question'} and subject['kind'] == 'loop',
            'Core loop subject')
    digest(subject['identity'], 'loop definition')
    digest(subject['question'], 'loop question')
    initializer, controller = packet['initializer'], packet['controller']
    layout = core.validate(initializer)
    require(core.validate(controller) == layout and initializer['inputs'] == controller['inputs']
            and initializer['prefix'] == controller['prefix'] and initializer['input-encoding'] == controller['input-encoding']
            == 'record-paths-v2' and all(item['subject']['kind'] == 'core' for item in (initializer, controller)),
            'exact shared loop Core layout')
    program = packet['program']
    inputs, state, expected_init, expected_step = reconstructed_program(program, dict(initializer['errors']), dict(controller['errors']))
    require(initializer['body'] == expected_init and controller['body'] == expected_step,
            'finite Core programs differ from the contained loop control')
    require({name: sort for name, sort, _ in initializer['inputs']} == {**inputs, **state, 'result': program['sort']},
            'exact declared inputs, state and result slot')
    names = {name: term['data'] for name, _, term in initializer['inputs']}
    prefix = initializer['prefix']
    to_original = {encoded: prefix + '.' + name for name, encoded in names.items()}
    original = tuple([to_original[name] for name in slots] for slots in layout)
    policy = packet['policy']
    require(type(policy) is dict and set(policy) == {'requires', 'invariant', 'ensures', 'rank'}
            and type(policy['rank']) is list and len(policy['rank']) <= 2, 'closed ranking policy')
    original_sorts = {prefix + '.' + name: sort[0] for name, sort in {**inputs, **state, 'result': program['sort']}.items()}
    for roots, sorts, allowed in [
            ([policy['requires']], ['bool'], inputs),
            ([policy['invariant'], *policy['rank']], ['bool', *['int'] * len(policy['rank'])], {**inputs, **state}),
            ([policy['ensures']], ['bool'], {**inputs, **state, 'result': program['sort']})]:
        variables = terms.validate_roots(roots, sorts)
        require(all(original_sorts.get(name) == sort and name[len(prefix) + 1:] in allowed
                    for name, sort in variables.items()), 'loop policy term input scope')
    proof = packet['entailment']
    proof_layout = terms.validate(proof)
    require(subject['question'] == proof['normalized']['question']
            and all(set(used) <= set(full) for used, full in zip(proof_layout, layout)), 'exact loop question and named slots')
    require(canonical_identity(packet) == packet['identity'], 'canonical Core loop packet identity mismatch')
    return layout, original, proof_layout


def definitions(packet, layout, original, proof_layout):
    policy = packet['policy']
    prefix = packet['initializer']['prefix']
    def slot(name, sort):
        return ('Layout.' + sort[0], original[0 if sort == ['int'] else 1].index(prefix + '.' + name))
    state_slots = 'Layout.unit'
    for name, sort in reversed(packet['initializer']['body']['sort'][1]):
        state_slots = ('Layout.pair', slot(name, sort), state_slots)
    ranks = policy['rank'] + [{'formal/term': 1, 'op': 'int', 'sort': ['int'], 'args': [], 'data': 0}] * (2 - len(policy['rank']))
    mappings = [[full.index(name) for name in used] for full, used in zip(layout, proof_layout)]
    return [
        ('stateSlots', state_slots), ('resultSlot', slot('result', packet['program']['sort'])),
        ('loopPre', policy['requires']), ('loopInv', policy['invariant']), ('rankFirst', ranks[0]),
        ('rankSecond', ranks[1]), ('loopPost', policy['ensures']),
        ('integerSlots : List Nat', mappings[0]), ('booleanSlots : List Nat', mappings[1])]


def source(packet, layouts):
    _, original, _ = layouts
    return HEADER + ''.join('\n\ndef ' + name + ' :=\n' +
                            (terms.emit_term(data, *original) if type(data) is dict else core.render(data))
                            for name, data in definitions(packet, *layouts)) + TAIL


def verify_source(text, packet, layouts):
    require(text.startswith(HEADER) and text.endswith(TAIL), 'fixed Core loop theorem template')
    rows = text[len(HEADER):-len(TAIL)].split('\n\ndef ')
    require(rows.pop(0) == '', 'Core loop declarations start')
    expected = definitions(packet, *layouts)
    require(len(rows) == len(expected), 'exact Core loop declarations')
    for row, (name, data) in zip(rows, expected):
        prefix = name + ' :=\n'
        require(row.startswith(prefix), 'Core loop declaration type')
        decoder = core.Decoder(row[len(prefix):])
        if type(data) is dict:
            require(terms.faithful(data, decoder.term(), *layouts[1]), 'generated loop policy term differs')
        else:
            require(decoder.data() == data, 'generated loop state or proof slot layout differs')
        require(decoder.at == len(decoder.tokens), 'trailing Core loop declaration data')


def checked_kernel():
    lean, libraries = core.checked_kernel()
    pin = json.loads((P / 'metatheory/core-loop-pin.json').read_text())
    for key in ('source', 'compiled', 'core_contract', 'loop_total'):
        require(k.sha(P / pin[key]['path']) == pin[key]['sha256'], 'Core loop model dependency pin')
    for module, key, required in [('CoreContract', 'core_contract', 'core_terms'), ('LoopTotal', 'loop_total', 'core')]:
        dependency = json.loads((P / pin[key]['path']).read_text())
        expected = {'core_terms': 'metatheory/core-terms-pin.json', 'core': 'evidence/specialization/model-qualification.json'}
        path = expected[required]
        require(dependency[required] == {'path': path, 'sha256': k.sha(P / path)}, 'shared typed Core dependency')
        for field in ('source', 'compiled'):
            require(k.sha(P / dependency[field]['path']) == dependency[field]['sha256'], 'Core loop theorem artifact pin')
        libraries[module] = dependency
    libraries['CoreLoop'] = pin
    return lean, libraries


def run(path, output, axiom_policy='lean-standard'):
    require(axiom_policy in terms.AXIOM_POLICIES, 'supported Core loop axiom policy')
    output.mkdir(parents=True, exist_ok=True)
    module = 'CoreLoopCheck'
    for name in (module + '.olean', 'result.json', 'lean.txt'):
        (output / name).unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'Core loop packet byte capacity')
    packet = k.load_packet(path)
    layouts = validate(packet)
    text = source(packet, layouts)
    verify_source(text, packet, layouts)
    lean, libraries = checked_kernel()
    imported, audits = check_linked(packet, text, output, module=module,
        premises=[('initializer', 'InitializerCore'), ('controller', 'ControllerCore'), ('entailment', 'EntailmentCheck')],
        lean=lean, libraries=libraries, axiom_policy=axiom_policy, expected_audits=AUDITS,
        failure='Lean did not accept the exact Core loop composition')
    result = {'schema': 'enchant.formal.core-loop-execution.v1', 'status': 'checked-core-loop-return',
              'packet': packet['identity'], 'subject': packet['subject'],
              'scope': 'finite-normal-return-of-the-contained-ranked-core-controller-on-admitted-inputs',
              'iteration_bound': None, 'imported_olean_sha256': imported, 'axioms': audits, 'axiom_policy': axiom_policy,
              'source_sha256': k.sha(output / (module + '.lean')), 'olean_sha256': k.sha(output / (module + '.olean')),
              'subject_connection': 'requires-fresh-BL-reconstruction',
              'source_compiler_preservation': 'not-established', 'compiler_proof_authority': False}
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
        print(json.dumps({key: result[key] for key in ('status', 'packet', 'axioms')}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
