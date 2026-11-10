import Check
import Witness

set_option maxRecDepth 5000
set_option maxHeartbeats 2000000
open FormalTerms FormalWitness

def chosenWitness : Witness :=
(Witness.mk [(Int.ofNat 0)] [])

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
