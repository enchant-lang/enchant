"""Compose fresh checked Core and entailment objects for an exact contract."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import core_term_check as core
from obligation_proof import data_digest, digest, typed_term_packet
import term_refutation as terms
import witness_kernel as witnesses

P, k, require = terms.P, terms.k, terms.require
HEADER = """import CoreCheck
import EntailmentCheck
import CoreContract
"""
BODY = """
set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract

"""
THEOREMS = """

def mapInt (n : Nat) : Nat := integerSlots[n]?.getD 0
def mapBool (n : Nat) : Nat := booleanSlots[n]?.getD 0

theorem exactContractQuestion :
    renameQuestion originalQuestion mapInt mapBool =
      policyQuestion contractPre contractPost symbolicOK symbolicError mustReturn declaredAllowed := rfl

theorem allowedPositive : ∀ n ∈ declaredAllowed, 0 < n := by
  have checked : declaredAllowed.all (fun n => decide (0 < n)) = true := by decide
  simpa only [List.all_eq_true, decide_eq_true_eq] using checked

theorem originalCoreSatisfiesContract : ∀ i b, contractPre.eval i b = some true →
    holds (BeamLispCore.eval originalProgram (originalInputs i b)) (symbolicValue.eval i b)
      (contractPost.eval i b) mustReturn declaredAllowed :=
  composed_contract originalProgram originalInputs contractPre contractPost symbolicOK symbolicValue symbolicError
    mustReturn declaredAllowed errorCodes allowedPositive coreTermCorrespondence
    (exactContractQuestion ▸ rename_entails originalQuestion mapInt mapBool originalQuestionEntails)

#print axioms exactContractQuestion
#print axioms allowedPositive
#print axioms originalCoreSatisfiesContract
"""
WITNESS = """

theorem chosenAdmitted : contractPre.eval chosenWitness.integerEnv chosenWitness.booleanEnv = some true := by decide

theorem originalCoreHasAdmittedOutcome : ∃ i b, contractPre.eval i b = some true ∧
    holds (BeamLispCore.eval originalProgram (originalInputs i b)) (symbolicValue.eval i b)
      (contractPost.eval i b) mustReturn declaredAllowed :=
  ⟨chosenWitness.integerEnv, chosenWitness.booleanEnv, chosenAdmitted,
    originalCoreSatisfiesContract _ _ chosenAdmitted⟩

#print axioms chosenAdmitted
#print axioms originalCoreHasAdmittedOutcome
"""


def canonical_identity(packet):
    data = {**packet, 'profile': k.Keyword(packet['profile']), 'identity-profile': k.Keyword(packet['identity-profile']),
            'core': core.typed_packet(packet['core']), 'entailment': typed_term_packet(packet['entailment']),
            'policy': {**packet['policy'], **{name: terms.typed_term(packet['policy'][name]) for name in ('pre', 'post')}},
            'witness': None if packet['witness'] is None else witnesses.typed_packet(packet['witness'])}
    del data['identity']
    return data_digest(data)


def validate(packet):
    require(type(packet) is dict and set(packet) == {'formal/core-contract-data', 'profile', 'identity-profile',
            'identity', 'core', 'entailment', 'policy', 'witness-question', 'witness'}, 'Core contract packet fields')
    require(type(packet['formal/core-contract-data']) is int and packet['formal/core-contract-data'] == 1
            and packet['profile'] == 'bl/core-contract-data-v1'
            and packet['identity-profile'] == 'bl/canonical-formal-data-v1', 'Core contract packet profile')
    digest(packet['identity'], 'Core contract packet')
    digest(packet['witness-question'], 'feasibility question')
    core_layout = core.validate(packet['core'])
    proof_layout = terms.validate(packet['entailment'])
    subject = packet['core']['subject']
    require(subject['kind'] == 'contract' and subject['question'] == packet['entailment']['normalized']['question'],
            'Core outcome and proof must refer to the same contract question')
    require(all(set(proof_names) <= set(core_names) for proof_names, core_names in zip(proof_layout, core_layout)),
            'entailment names and sorts belong to the Core input layout')
    policy = packet['policy']
    require(type(policy) is dict and set(policy) == {'pre', 'post', 'must-return', 'allowed-codes'}
            and type(policy['must-return']) is bool, 'closed Core contract policy')
    allowed = policy['allowed-codes']
    require(type(allowed) is list and len(allowed) <= len(packet['core']['errors'])
            and all(type(code) is int and code > 0 for code in allowed), 'positive allowed Core error codes')
    require(allowed == sorted(set(allowed)) and set(allowed) <= {code for _, code in packet['core']['errors']},
            'ordered unique allowed codes drawn from the Core catalogue')
    names = terms.validate_roots([policy['pre'], policy['post']], ['bool', 'bool'])
    require(all(name in core_layout[sort == 'bool'] for name, sort in names.items()),
            'contract policy names and sorts belong to the Core input layout')
    witness = packet['witness']
    if witness is not None:
        witnesses.validate(witness)
        require(witness['question'] == packet['witness-question'] and witness['assertions'] == packet['entailment']['assertions'],
                'witness belongs to the exact contract feasibility context')
    require(canonical_identity(packet) == packet['identity'], 'canonical Core contract packet identity mismatch')
    return core_layout, proof_layout


def layout_definitions(packet, core_layout, proof_layout):
    policy = packet['policy']
    slots = [[names.index(name) for name in used] for names, used in zip(core_layout, proof_layout)]
    return [('contractPre : Term FormalTerms.Ty.boolean', policy['pre']),
            ('contractPost : Term FormalTerms.Ty.boolean', policy['post']),
            ('mustReturn : Bool', policy['must-return']),
            ('declaredAllowed : List Nat', policy['allowed-codes']),
            ('integerSlots : List Nat', slots[0]), ('booleanSlots : List Nat', slots[1])]


def projected_values(witness, integers, booleans):
    values = {name: value for name, _, value in witness['bindings']}
    return [values.get(name, 0) for name in integers], [values.get(name, False) for name in booleans]


def boundaries(packet):
    return ((HEADER + 'import Witness\n' + BODY, WITNESS) if packet['witness'] is not None
            else (HEADER + BODY, THEOREMS))


def source(packet, core_layout, proof_layout):
    header, _ = boundaries(packet)
    definitions = layout_definitions(packet, core_layout, proof_layout)
    declarations = ''.join('\ndef ' + name + ' :=\n' +
                           (terms.emit_term(data, *core_layout) if type(data) is dict else core.render(data)) + '\n'
                           for name, data in definitions)
    text = header + declarations + THEOREMS
    if packet['witness'] is not None:
        text += '\nopen FormalWitness\n\ndef chosenWitness : Witness :=\n'
        text += witnesses.emit_witness(*projected_values(packet['witness'], *core_layout)) + WITNESS
    return text


def verify_source(text, packet, core_layout, proof_layout):
    header, tail = boundaries(packet)
    require(text.startswith(header) and text.endswith(tail), 'fixed Core contract theorem template')
    if packet['witness'] is not None:
        marker = THEOREMS + '\nopen FormalWitness\n\ndef chosenWitness : Witness :=\n'
        declarations, witness = text[len(header):-len(tail)].split(marker)
        require(witnesses.decode_witness(witness) == projected_values(packet['witness'], *core_layout),
                'generated witness differs from the named Core projection')
    else:
        declarations = text[len(header):-len(tail)]
    rows = declarations.split('\ndef ')
    require(rows.pop(0) == '', 'Core contract definitions start')
    expected = layout_definitions(packet, core_layout, proof_layout)
    require(len(rows) == len(expected), 'exact Core contract declarations')
    for row, (name, data) in zip(rows, expected):
        prefix = name + ' :=\n'
        require(row.startswith(prefix), 'Core contract declaration type')
        parser = core.Decoder(row[len(prefix):])
        if type(data) is dict:
            require(terms.faithful(data, parser.term(), *core_layout), 'generated precondition or postcondition differs')
        else:
            require(parser.data() == data, 'generated policy or input slots differ')
        require(parser.at == len(parser.tokens), 'trailing Core contract declaration data')


def checked_kernel(with_witness):
    lean, libraries = core.checked_kernel()
    pin = json.loads((P / 'metatheory/core-contract-pin.json').read_text())
    for key in ['source', 'compiled', 'core_terms', 'witness']:
        require(k.sha(P / pin[key]['path']) == pin[key]['sha256'], 'Core contract model dependency pin')
    libraries['CoreContract'] = pin
    if with_witness:
        witness_lean, witness_pins = witnesses.checked_kernel()
        require(witness_lean == lean and witness_pins[:2] == [libraries['Refutation'], libraries['Terms']],
                'shared witness term model libraries')
        libraries['Witness'] = witness_pins[-1]
    return lean, libraries


def run(path, output, axiom_policy='lean-standard'):
    require(axiom_policy in terms.AXIOM_POLICIES, 'supported Core contract axiom policy')
    output.mkdir(parents=True, exist_ok=True)
    for name in ['CoreContractCheck.olean', 'result.json', 'lean.txt']:
        (output / name).unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'Core contract packet byte capacity')
    packet = k.load_packet(path)
    core_layout, proof_layout = validate(packet)
    text = source(packet, core_layout, proof_layout)
    verify_source(text, packet, core_layout, proof_layout)
    with_witness = packet['witness'] is not None
    lean, libraries = checked_kernel(with_witness)
    (output / 'CoreContractCheck.lean').write_text(text)
    with tempfile.TemporaryDirectory(prefix='enchant-core-contract-') as temporary:
        work = Path(temporary)
        library = work / 'library'
        core.copy_library(library, libraries)
        core_input = work / 'core.json'
        core_input.write_text(json.dumps(packet['core']))
        proof_input = work / 'entailment.json'
        proof_input.write_text(json.dumps(packet['entailment']))
        core_result = core.run(core_input, output / 'core', axiom_policy, module='CoreCheck')
        proof_result = terms.run(proof_input, output / 'entailment', axiom_policy, module='EntailmentCheck')
        for directory, module, identity in [('core', 'CoreCheck', core_result['olean_sha256']),
                                             ('entailment', 'EntailmentCheck', proof_result['proof_olean_sha256'])]:
            target = library / (module + '.olean')
            shutil.copyfile(output / directory / 'Check.olean', target)
            require(k.sha(target) == identity, 'fresh contract premise object identity')
        check = work / 'CoreContractCheck.lean'
        check.write_text(text)
        compiled = check.with_suffix('.olean')
        with (output / 'lean.txt').open('w') as log:
            completed = subprocess.run([str(lean), '--root=' + str(work), '-o', str(compiled), str(check)],
                                       cwd=work, env=dict(os.environ, LEAN_PATH=str(library)), stdout=log,
                                       stderr=subprocess.STDOUT, timeout=120)
        transcript = (output / 'lean.txt').read_text()
        require(completed.returncode == 0 and 'sorryAx' not in transcript and 'warning:' not in transcript,
                'Lean did not accept the exact Core contract composition')
        expected = {'exactContractQuestion', 'allowedPositive', 'originalCoreSatisfiesContract'}
        if with_witness:
            expected.update({'chosenAdmitted', 'originalCoreHasAdmittedOutcome'})
        audits = witnesses.theorem_audits(transcript, expected)
        require(all(set(deps) <= terms.AXIOM_POLICIES[axiom_policy] for deps in audits.values()), 'Core contract axioms exceed policy')
        shutil.copyfile(compiled, output / compiled.name)
    result = {'schema': 'enchant.formal.core-contract-execution.v1', 'status': 'checked-core-contract',
              'packet': packet['identity'], 'subject': packet['core']['subject'],
              'scope': 'original-contained-core-contract-on-admitted-inputs',
              'imported_core_sha256': core_result['olean_sha256'], 'imported_entailment_sha256': proof_result['proof_olean_sha256'],
              'witness': packet['witness']['identity'] if with_witness else None,
              'admission': 'checked-precondition-witness' if with_witness else 'witness-not-provided',
              'source_sha256': k.sha(output / check.name), 'olean_sha256': k.sha(output / compiled.name),
              'axioms': audits, 'axiom_policy': axiom_policy,
              'source_data': 'independently-decoded-and-compared', 'subject_connection': 'requires-fresh-BL-reconstruction',
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
        print(json.dumps({key: result[key] for key in ('status', 'packet', 'admission', 'axioms')}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
