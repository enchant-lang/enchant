"""Check equality of two exact Core outcomes under a portable precondition."""
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
from witness_kernel import theorem_audits

P, k, require = terms.P, terms.k, terms.require
HEADER = """import BeforeCore
import AfterCore
import EntailmentCheck
import CoreTranslation

set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreTranslation
"""
TAIL = """

def mapInt (n : Nat) : Nat := integerSlots[n]?.getD 0
def mapBool (n : Nat) : Nat := booleanSlots[n]?.getD 0

theorem exactTranslationQuestion :
    renameQuestion originalQuestion mapInt mapBool =
      comparisonQuestion translationPre BeforeCore.symbolicOK AfterCore.symbolicOK
        BeforeCore.symbolicValue AfterCore.symbolicValue BeforeCore.symbolicError AfterCore.symbolicError := rfl

theorem sameCoreInputs : AfterCore.originalInputs = BeforeCore.originalInputs := rfl
theorem sameErrorCatalogue : AfterCore.errorCodes = BeforeCore.errorCodes := rfl

theorem beforeErrorsCovered :
    covers (BeforeCore.errorCodes.map errorName) BeforeCore.originalProgram = true := by decide

theorem afterErrorsCovered :
    covers (BeforeCore.errorCodes.map errorName) AfterCore.originalProgram = true := by decide

theorem originalCoreOutcomesEqual : ∀ i b, translationPre.eval i b = some true →
    eval BeforeCore.originalProgram (BeforeCore.originalInputs i b) =
      eval AfterCore.originalProgram (AfterCore.originalInputs i b) := by
  have afterAgreement : ∀ i b, agrees (eval AfterCore.originalProgram (BeforeCore.originalInputs i b))
      (AfterCore.symbolicOK.eval i b) (AfterCore.symbolicValue.eval i b)
      (AfterCore.symbolicError.eval i b) (errorCode BeforeCore.errorCodes) := by
    simpa only [sameCoreInputs, sameErrorCatalogue] using AfterCore.coreTermCorrespondence
  rw [sameCoreInputs]
  exact composed_translation BeforeCore.originalProgram AfterCore.originalProgram BeforeCore.originalInputs
    BeforeCore.errorCodes translationPre BeforeCore.symbolicOK AfterCore.symbolicOK
    BeforeCore.symbolicValue AfterCore.symbolicValue BeforeCore.symbolicError AfterCore.symbolicError
    BeforeCore.coreTermCorrespondence afterAgreement beforeErrorsCovered afterErrorsCovered
    (exactTranslationQuestion ▸ rename_entails originalQuestion mapInt mapBool originalQuestionEntails)

#print axioms exactTranslationQuestion
#print axioms sameCoreInputs
#print axioms sameErrorCatalogue
#print axioms beforeErrorsCovered
#print axioms afterErrorsCovered
#print axioms originalCoreOutcomesEqual
"""
AUDITS = {'exactTranslationQuestion', 'sameCoreInputs', 'sameErrorCatalogue',
          'beforeErrorsCovered', 'afterErrorsCovered', 'originalCoreOutcomesEqual'}


def canonical_identity(packet):
    subject = packet['subject']
    data = {**packet, 'profile': k.Keyword(packet['profile']), 'identity-profile': k.Keyword(packet['identity-profile']),
            'subject': {**subject, 'kind': k.Keyword(subject['kind']), 'relation': k.Keyword(subject['relation'])},
            'pre': terms.typed_term(packet['pre']), 'before': core.typed_packet(packet['before']),
            'after': core.typed_packet(packet['after']), 'entailment': typed_term_packet(packet['entailment'])}
    del data['identity']
    return data_digest(data)


def validate(packet):
    require(type(packet) is dict and set(packet) == {'formal/core-translation-data', 'profile', 'identity-profile',
            'identity', 'subject', 'pre', 'before', 'after', 'entailment'}, 'Core translation packet fields')
    require(type(packet['formal/core-translation-data']) is int and packet['formal/core-translation-data'] == 1
            and packet['profile'] == 'bl/core-translation-data-v1'
            and packet['identity-profile'] == 'bl/canonical-formal-data-v1', 'Core translation packet profile')
    digest(packet['identity'], 'Core translation packet')
    subject = packet['subject']
    require(type(subject) is dict and set(subject) == {'kind', 'identity', 'before', 'after', 'question', 'relation'}
            and subject['kind'] == 'translation' and subject['relation'] == 'return-value-and-named-error', 'Core translation subject')
    for name in ('identity', 'before', 'after', 'question'):
        digest(subject[name], name)
    before, after = packet['before'], packet['after']
    core_layout = core.validate(before)
    after_layout = core.validate(after)
    for side, model in [('before', before), ('after', after)]:
        require(model['subject']['kind'] == 'core' and model['core'] == subject[side], 'exact before and after Core identities')
    require(core_layout == after_layout and all(before[key] == after[key] for key in ('inputs', 'prefix', 'input-encoding')),
            'both Core trees must use the same named input layout')
    require(before['errors'] == after['errors'], 'both Core trees must use the same named error catalogue')
    require(before['body']['sort'] == after['body']['sort'], 'both Core trees must have the same named result sort')
    proof = packet['entailment']
    proof_layout = terms.validate(proof)
    require(subject['question'] == proof['normalized']['question'], 'same original translation question')
    require(all(set(used) <= set(names) for used, names in zip(proof_layout, core_layout)),
            'entailment inputs belong to the Core layout with the same sorts')
    named_sorts = {name: sort for names, sort in zip(core_layout, ('int', 'bool')) for name in names}
    pre_names = terms.validate_roots([packet['pre']], ['bool'])
    require(all(named_sorts.get(name) == sort for name, sort in pre_names.items()), 'precondition inputs belong to the Core layout')
    require(canonical_identity(packet) == packet['identity'], 'canonical Core translation packet identity mismatch')
    return core_layout, proof_layout


def definitions(packet, core_layout, proof_layout):
    slots = [[names.index(name) for name in used] for names, used in zip(core_layout, proof_layout)]
    return [('translationPre : Term FormalTerms.Ty.boolean', packet['pre']),
            ('integerSlots : List Nat', slots[0]), ('booleanSlots : List Nat', slots[1])]


def source(packet, core_layout, proof_layout):
    return HEADER + ''.join('\n\ndef ' + name + ' :=\n' +
                            (terms.emit_term(data, *core_layout) if type(data) is dict else core.render(data))
                            for name, data in definitions(packet, core_layout, proof_layout)) + TAIL


def verify_source(text, packet, core_layout, proof_layout):
    require(text.startswith(HEADER) and text.endswith(TAIL), 'fixed Core translation theorem template')
    rows = text[len(HEADER):-len(TAIL)].split('\n\ndef ')
    require(rows.pop(0) == '', 'Core translation definitions start')
    expected = definitions(packet, core_layout, proof_layout)
    require(len(rows) == len(expected), 'exact Core translation declarations')
    for row, (name, data) in zip(rows, expected):
        prefix = name + ' :=\n'
        require(row.startswith(prefix), 'Core translation declaration type')
        decoder = core.Decoder(row[len(prefix):])
        if type(data) is dict:
            require(terms.faithful(data, decoder.term(), *core_layout), 'generated translation precondition differs')
        else:
            require(decoder.data() == data, 'generated translation input slots differ')
        require(decoder.at == len(decoder.tokens), 'trailing Core translation declaration data')


def checked_kernel():
    lean, libraries = core.checked_kernel()
    pin = json.loads((P / 'metatheory/core-translation-pin.json').read_text())
    for key in ('source', 'compiled', 'core_terms', 'core_contract'):
        require(k.sha(P / pin[key]['path']) == pin[key]['sha256'], 'Core translation model dependency pin')
    contract = json.loads((P / pin['core_contract']['path']).read_text())
    require(contract['core_terms'] == pin['core_terms'], 'shared Core term model dependency')
    for key in ('source', 'compiled'):
        require(k.sha(P / contract[key]['path']) == contract[key]['sha256'], 'Core contract model artifact pin')
    libraries.update(CoreContract=contract, CoreTranslation=pin)
    return lean, libraries


def run(path, output, axiom_policy='lean-standard'):
    require(axiom_policy in terms.AXIOM_POLICIES, 'supported Core translation axiom policy')
    output.mkdir(parents=True, exist_ok=True)
    module = 'CoreTranslationCheck'
    for name in (module + '.olean', 'result.json', 'lean.txt'):
        (output / name).unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'Core translation packet byte capacity')
    packet = k.load_packet(path)
    layouts = validate(packet)
    text = source(packet, *layouts)
    verify_source(text, packet, *layouts)
    lean, libraries = checked_kernel()
    (output / (module + '.lean')).write_text(text)
    with tempfile.TemporaryDirectory(prefix='enchant-core-translation-') as temporary:
        work = Path(temporary)
        library = work / 'library'
        core.copy_library(library, libraries)
        imported = {}
        for side, premise_module, check_premise, object_hash in [
                ('before', 'BeforeCore', core.run, 'olean_sha256'),
                ('after', 'AfterCore', core.run, 'olean_sha256'),
                ('entailment', 'EntailmentCheck', terms.run, 'proof_olean_sha256')]:
            input_path = work / (side + '.json')
            input_path.write_text(json.dumps(packet[side]))
            premise_output = output / side
            result = check_premise(input_path, premise_output, axiom_policy, module=premise_module)
            target = library / (premise_module + '.olean')
            shutil.copyfile(premise_output / 'Check.olean', target)
            require(k.sha(target) == result[object_hash], 'fresh translation premise object identity')
            imported[side] = result[object_hash]
        check = work / (module + '.lean')
        check.write_text(text)
        compiled = check.with_suffix('.olean')
        with (output / 'lean.txt').open('w') as log:
            completed = subprocess.run([str(lean), '--root=' + str(work), '-o', str(compiled), str(check)],
                                       cwd=work, env=dict(os.environ, LEAN_PATH=str(library)), stdout=log,
                                       stderr=subprocess.STDOUT, timeout=120)
        transcript = (output / 'lean.txt').read_text()
        require(completed.returncode == 0 and 'sorryAx' not in transcript and 'warning:' not in transcript,
                'Lean did not accept the exact Core translation composition')
        audits = theorem_audits(transcript, AUDITS)
        require(all(set(deps) <= terms.AXIOM_POLICIES[axiom_policy] for deps in audits.values()), 'Core translation axioms exceed policy')
        shutil.copyfile(compiled, output / compiled.name)
    result = {'schema': 'enchant.formal.core-translation-execution.v1', 'status': 'checked-core-translation',
              'packet': packet['identity'], 'subject': packet['subject'],
              'scope': 'conditional-equality-of-the-two-contained-core-outcomes',
              'imported_olean_sha256': imported, 'axioms': audits, 'axiom_policy': axiom_policy,
              'source_sha256': k.sha(output / check.name), 'olean_sha256': k.sha(output / compiled.name),
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
        print(json.dumps({key: result[key] for key in ('status', 'packet', 'axioms')}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
