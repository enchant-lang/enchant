import ActorTrace

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
set_option linter.unusedSimpArgs false
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop ActorTrace
set_option linter.unusedVariables false

namespace CoreObservedTrace


def stateSlots :=
(Layout.pair (Layout.int 0) Layout.unit)

def stateIntCount : Nat :=
1

def stateBoolCount : Nat :=
0

def initialPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.bool true) (Term.and (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 0))) (Term.bool true)))

def invariantPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.and (Term.bool true) (Term.and (Term.lt (Term.int (Int.ofNat 0)) (Term.inputInt 0)) (Term.bool true))) (Term.bool true))

def policy := StatePolicy.mk stateSlots stateIntCount stateBoolCount initialPredicate invariantPredicate


def handlers : List (Handler (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) := []

def recordedInputs (integers : List Int) (booleans : List Bool) : Inputs :=
  ⟨fun n => integers[n]?.getD 0, fun n => booleans[n]?.getD false⟩

def projectedFailure : Option String := some "zero-divisor"


def recordedConfig0 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvents : List (Event handlers) :=
[]

def recordedConfigurations : List (Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) :=
[recordedConfig0]

theorem recordedPrefix0 : Trace handlers policy.initial (recordedEvents.take 0) (recordedConfigurations.get ⟨0, by decide⟩) :=
  Trace.start (by rfl)

theorem recordedInvariant0 : ¬ policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 := by
  unfold StatePolicy.invariant ActorTrace.holds
  decide

theorem recordedUnsafePrefix : ¬ (policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 ∧ (recordedConfigurations.get ⟨0, by decide⟩).2 = none) :=
  fun safe => recordedInvariant0 safe.1

end CoreObservedTrace

#print axioms CoreObservedTrace.recordedInvariant0
#print axioms CoreObservedTrace.recordedPrefix0
#print axioms CoreObservedTrace.recordedUnsafePrefix
