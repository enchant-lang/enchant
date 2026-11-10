"""Apply a freshly checked typed entailment to an explicit witness."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import term_refutation as terms
import witness_kernel as witnesses

require = terms.require
HEADER = '''import Check
import Witness

set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def chosenWitness : Witness :=
'''
TAIL = '''

theorem chosenWitnessAccepted : accepts originalQuestion.assertions chosenWitness = true := by decide

theorem chosenClaim : originalQuestion.claim.eval chosenWitness.integerEnv chosenWitness.booleanEnv = some true :=
  originalQuestionEntails chosenWitness.integerEnv chosenWitness.booleanEnv
    (checked_context_holds originalQuestion.assertions chosenWitness chosenWitnessAccepted)

theorem originalQuestionHasSatisfyingClaim : ∃ integers booleans,
    originalQuestion.assumed integers booleans ∧ originalQuestion.claim.eval integers booleans = some true :=
  ⟨chosenWitness.integerEnv, chosenWitness.booleanEnv,
    checked_context_holds originalQuestion.assertions chosenWitness chosenWitnessAccepted, chosenClaim⟩

#print axioms chosenWitnessAccepted
#print axioms chosenClaim
#print axioms originalQuestionHasSatisfyingClaim
'''


def project(packet, witness):
    integers, booleans = terms.validate(packet)
    witnesses.validate(witness)
    named = {name: (sort[0], value) for name, sort, value in witness['bindings']}
    require(all((name in integers if sort == 'int' else name in booleans) for name, (sort, _) in named.items()),
            'witness names and sorts must occur in the entailment layout')
    return ([named.get(name, ('int', 0))[1] for name in integers],
            [named.get(name, ('bool', False))[1] for name in booleans])


def run(proof, proof_entry, proof_object, witness, output):
    """Use the entailment object emitted during this run's leaf checks."""
    output.mkdir(parents=True, exist_ok=True)
    (output / 'Instance.olean').unlink(missing_ok=True)
    (output / 'result.json').unlink(missing_ok=True)
    require(proof['identity'] == proof_entry['packet'], 'fresh entailment packet identity')
    integers, booleans = project(proof, witness)
    text = HEADER + witnesses.emit_witness(integers, booleans) + TAIL
    require(text.startswith(HEADER) and text.endswith(TAIL) and
            witnesses.decode_witness(text[len(HEADER):-len(TAIL)]) == (integers, booleans),
            'generated instance values differ from the named witness projection')
    lean, pins = witnesses.checked_kernel()
    (output / 'Instance.lean').write_text(text)
    with tempfile.TemporaryDirectory(prefix='enchant-obligation-instance-') as temporary:
        work = Path(temporary)
        library = work / 'library'
        witnesses.copy_library(library, pins)
        imported = library / 'Check.olean'
        shutil.copyfile(proof_object, imported)
        require(terms.k.sha(imported) == proof_entry['proof_olean_sha256'], 'fresh entailment object identity')
        source = work / 'Instance.lean'
        source.write_text(text)
        with (output / 'lean.txt').open('w') as log:
            completed = subprocess.run([str(lean), '--root=' + str(work), '-o', str(work / 'Instance.olean'), str(source)],
                                       cwd=work, env=dict(os.environ, LEAN_PATH=str(library)),
                                       stdout=log, stderr=subprocess.STDOUT, timeout=120)
        transcript = (output / 'lean.txt').read_text()
        require(completed.returncode == 0 and 'sorryAx' not in transcript and 'warning:' not in transcript,
                'Lean did not accept the witnessed entailment instance')
        audits = witnesses.theorem_audits(transcript, {'chosenWitnessAccepted', 'chosenClaim', 'originalQuestionHasSatisfyingClaim'})
        policy = terms.AXIOM_POLICIES[proof_entry['axiom_policy']]
        require(all(set(dependencies) <= policy for dependencies in audits.values()), 'instance axiom dependencies exceed policy')
        shutil.copyfile(work / 'Instance.olean', output / 'Instance.olean')
    result = {'schema': 'enchant.formal.obligation-instance-execution.v1',
              'status': 'checked-original-question-satisfying-claim',
              'question': proof['normalized']['question'], 'proof_packet': proof['identity'], 'witness_packet': witness['identity'],
              'imported_entailment_sha256': proof_entry['proof_olean_sha256'],
              'source_sha256': terms.k.sha(output / 'Instance.lean'), 'olean_sha256': terms.k.sha(output / 'Instance.olean'),
              'axioms': audits, 'axiom_policy': proof_entry['axiom_policy'],
              'completion': 'zero-false-for-inputs-absent-from-witness', 'compiler_proof_authority': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
