import ActorTrace

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
set_option linter.unusedSimpArgs false
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop ActorTrace
set_option linter.unusedVariables false

namespace CoreObservedTrace

namespace ActorHandlerCore0


def originalProgram : Expr [(BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit), (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)] (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(localExpr (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) Var.zero)

def originalInputs (i : Nat → Int) (b : Nat → Bool) : Env [(BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit), (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)] :=
(Env.cons (Prod.mk (i 1) Unit.unit) (Env.cons (Prod.mk (i 0) Unit.unit) Env.nil))
end ActorHandlerCore0


def stateSlots :=
(Layout.pair (Layout.int 0) Layout.unit)

def stateIntCount : Nat :=
1

def stateBoolCount : Nat :=
0

def initialPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.bool true) (Term.and (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 0))) (Term.bool true)))

def invariantPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0)) (Term.bool true))) (Term.bool true))

def admission0 : Term FormalTerms.Ty.boolean :=
(Term.bool true)

def policy := StatePolicy.mk stateSlots stateIntCount stateBoolCount initialPredicate invariantPredicate


def handlerEnv0 (input : Inputs) := ActorHandlerCore0.originalInputs input.ints input.bools
def handler0 := coreHandler policy ActorHandlerCore0.originalProgram handlerEnv0 admission0

theorem handler0ReadsState (value : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) (message : Inputs) :
    (handlerEnv0 (stateSlots.put value message)).lookup (Var.succ Var.zero) = value := rfl


def handlers : List (Handler (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) := [handler0]

def recordedInputs (integers : List Int) (booleans : List Bool) : Inputs :=
  ⟨fun n => integers[n]?.getD 0, fun n => booleans[n]?.getD false⟩

def projectedFailure : Option String := some "zero-divisor"


def recordedConfig0 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedHandler1 : Fin handlers.length :=
(Fin.mk 0 (by decide))

def recordedMessageValue1 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Int.negSucc 4) Unit.unit)

def recordedMessage1 : Inputs :=
(recordedInputs [(Int.ofNat 0), (Int.negSucc 4)] [])

def recordedEvent1 : Event handlers :=
(some (Prod.mk recordedHandler1 recordedMessage1))

def recordedConfig1 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.negSucc 4) Unit.unit) none)

def recordedHandler2 : Fin handlers.length :=
(Fin.mk 0 (by decide))

def recordedMessageValue2 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Int.ofNat 0) Unit.unit)

def recordedMessage2 : Inputs :=
(recordedInputs [(Int.ofNat 0), (Int.ofNat 0)] [])

def recordedEvent2 : Event handlers :=
(some (Prod.mk recordedHandler2 recordedMessage2))

def recordedConfig2 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvents : List (Event handlers) :=
[recordedEvent1, recordedEvent2]

def recordedConfigurations : List (Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) :=
[recordedConfig0, recordedConfig1, recordedConfig2]

theorem recordedPrefix0 : Trace handlers policy.initial (recordedEvents.take 0) (recordedConfigurations.get ⟨0, by decide⟩) :=
  Trace.start (by rfl)

theorem recordedInvariant0 : policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 := rfl

theorem recordedSafe0 : policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 ∧ (recordedConfigurations.get ⟨0, by decide⟩).2 = none :=
  ⟨recordedInvariant0, rfl⟩

theorem recordedMessage1Read :
    (handlerEnv0 (policy.slots.put recordedConfig0.1 recordedMessage1)).lookup Var.zero =
      recordedMessageValue1 := rfl

theorem recordedStep1 : Step handlers recordedConfig0 recordedEvent1 recordedConfig1 :=
  Step.returned recordedHandler1 recordedMessage1 (by rfl) (by rfl)

theorem recordedPrefix1 : Trace handlers policy.initial (recordedEvents.take 1) (recordedConfigurations.get ⟨1, by decide⟩) :=
  Trace.append recordedPrefix0 recordedStep1

theorem recordedInvariant1 : ¬ policy.invariant (recordedConfigurations.get ⟨1, by decide⟩).1 := by
  unfold StatePolicy.invariant ActorTrace.holds
  decide

theorem recordedMessage2Read :
    (handlerEnv0 (policy.slots.put recordedConfig1.1 recordedMessage2)).lookup Var.zero =
      recordedMessageValue2 := rfl

theorem recordedStep2 : Step handlers recordedConfig1 recordedEvent2 recordedConfig2 :=
  Step.returned recordedHandler2 recordedMessage2 (by rfl) (by rfl)

theorem recordedPrefix2 : Trace handlers policy.initial (recordedEvents.take 2) (recordedConfigurations.get ⟨2, by decide⟩) :=
  Trace.append recordedPrefix1 recordedStep2

theorem recordedInvariant2 : policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 := rfl

theorem recordedSafe2 : policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 ∧ (recordedConfigurations.get ⟨2, by decide⟩).2 = none :=
  ⟨recordedInvariant2, rfl⟩

theorem recordedUnsafePrefix : ¬ (policy.invariant (recordedConfigurations.get ⟨1, by decide⟩).1 ∧ (recordedConfigurations.get ⟨1, by decide⟩).2 = none) :=
  fun safe => recordedInvariant1 safe.1

end CoreObservedTrace

#print axioms CoreObservedTrace.handler0ReadsState
#print axioms CoreObservedTrace.recordedInvariant0
#print axioms CoreObservedTrace.recordedInvariant1
#print axioms CoreObservedTrace.recordedInvariant2
#print axioms CoreObservedTrace.recordedMessage1Read
#print axioms CoreObservedTrace.recordedMessage2Read
#print axioms CoreObservedTrace.recordedPrefix0
#print axioms CoreObservedTrace.recordedPrefix1
#print axioms CoreObservedTrace.recordedPrefix2
#print axioms CoreObservedTrace.recordedSafe0
#print axioms CoreObservedTrace.recordedSafe2
#print axioms CoreObservedTrace.recordedStep1
#print axioms CoreObservedTrace.recordedStep2
#print axioms CoreObservedTrace.recordedUnsafePrefix
