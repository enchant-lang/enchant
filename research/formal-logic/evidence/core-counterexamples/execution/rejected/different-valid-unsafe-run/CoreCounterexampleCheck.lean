import Check
import CoreObservedTrace

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
open BeamLispCore FormalTerms FormalRefutation FormalWitness CoreTerms CoreContract CoreLoop ActorTrace

namespace CoreCounterexampleCheck


def originalClaim : Term FormalTerms.Ty.boolean :=
(Term.and (Term.bool true) (Term.and (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 2)) (Term.bool true)))) (Term.bool true)) (Term.and (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 3)) (Term.bool true)))) (Term.bool true)) (Term.and (Term.and (Term.implies (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.bool true) (Term.and (Term.implies (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))) (Term.bool true)))) (Term.bool true)) (Term.and (Term.and (Term.implies (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 1))) (Term.and (Term.bool true) (Term.and (Term.implies (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))) (Term.bool true)))) (Term.bool true)) (Term.bool true))))) (Term.bool true)))

def assumptionCount : Nat :=
10

def projectedState0 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)) :=
(Prod.mk (suppliedWitness.integerEnv 2) (Prod.mk (suppliedWitness.booleanEnv 0) Unit.unit))

def projectedState1 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)) :=
(Prod.mk (suppliedWitness.integerEnv 3) (Prod.mk (suppliedWitness.booleanEnv 1) Unit.unit))

def projectedChoice0 : Int :=
(suppliedWitness.integerEnv 0)

def projectedMessage1 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.bool BeamLispCore.Ty.unit)) :=
(Prod.mk (suppliedWitness.integerEnv 1) (Prod.mk false Unit.unit))

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

theorem projectedState0Matches : projectedState0 = CoreObservedTrace.recordedConfig0.1 := rfl

theorem projectedState1Matches : projectedState1 = CoreObservedTrace.recordedConfig1.1 := rfl

theorem projectedChoice0Matches : projectedChoice0 = (Int.ofNat 1) := rfl

theorem projectedMessage1Matches : projectedMessage1 = CoreObservedTrace.recordedMessageValue1 := rfl

def projectionMatches : Prop :=
  projectedState0 = CoreObservedTrace.recordedConfig0.1 ∧
  projectedState1 = CoreObservedTrace.recordedConfig1.1 ∧
  projectedChoice0 = (Int.ofNat 1) ∧
  projectedMessage1 = CoreObservedTrace.recordedMessageValue1 ∧
  True

theorem sameProjection : projectionMatches :=
  ⟨projectedState0Matches, ⟨projectedState1Matches, ⟨projectedChoice0Matches, ⟨projectedMessage1Matches, True.intro⟩⟩⟩⟩

theorem originalCounterexampleRuns :
    originalQuestion.assumed suppliedWitness.integerEnv suppliedWitness.booleanEnv ∧
    originalQuestion.claim.eval suppliedWitness.integerEnv suppliedWitness.booleanEnv = some false ∧
    projectionMatches ∧
    Trace CoreObservedTrace.handlers CoreObservedTrace.policy.initial
      CoreObservedTrace.recordedEvents (CoreObservedTrace.recordedConfigurations.get ⟨1, by decide⟩) ∧
    ¬ (CoreObservedTrace.policy.invariant (CoreObservedTrace.recordedConfigurations.get ⟨1, by decide⟩).1 ∧
       (CoreObservedTrace.recordedConfigurations.get ⟨1, by decide⟩).2 = none) :=
  ⟨originalAssumptionsHold, originalClaimIsFalse, sameProjection,
    CoreObservedTrace.recordedPrefix1, CoreObservedTrace.recordedUnsafePrefix⟩

end CoreCounterexampleCheck

#print axioms CoreCounterexampleCheck.originalAssumptionsHold
#print axioms CoreCounterexampleCheck.originalClaimIsFalse
#print axioms CoreCounterexampleCheck.originalContextMatches
#print axioms CoreCounterexampleCheck.originalCounterexampleRuns
#print axioms CoreCounterexampleCheck.originalQueryHasCounterexample
#print axioms CoreCounterexampleCheck.projectedChoice0Matches
#print axioms CoreCounterexampleCheck.projectedMessage1Matches
#print axioms CoreCounterexampleCheck.projectedState0Matches
#print axioms CoreCounterexampleCheck.projectedState1Matches
#print axioms CoreCounterexampleCheck.sameProjection
