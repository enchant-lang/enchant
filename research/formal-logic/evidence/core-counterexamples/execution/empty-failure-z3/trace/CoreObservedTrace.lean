import ActorTrace

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
set_option linter.unusedSimpArgs false
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop ActorTrace
set_option linter.unusedVariables false

namespace CoreObservedTrace

namespace ActorHandlerCore0


def originalProgram : Expr [BeamLispCore.Ty.unit, BeamLispCore.Ty.unit] BeamLispCore.Ty.unit :=
(Expr.seq (Expr.intOp IntOp.quot (intLit (Int.ofNat 1)) (intLit (Int.ofNat 0))) unitLit)

def originalInputs (i : Nat → Int) (b : Nat → Bool) : Env [BeamLispCore.Ty.unit, BeamLispCore.Ty.unit] :=
(Env.cons Unit.unit (Env.cons Unit.unit Env.nil))
end ActorHandlerCore0


def stateSlots :=
Layout.unit

def stateIntCount : Nat :=
0

def stateBoolCount : Nat :=
0

def initialPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true)))

def invariantPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.bool true))) (Term.bool true))

def admission0 : Term FormalTerms.Ty.boolean :=
(Term.bool true)

def policy := StatePolicy.mk stateSlots stateIntCount stateBoolCount initialPredicate invariantPredicate


def handlerEnv0 (input : Inputs) := ActorHandlerCore0.originalInputs input.ints input.bools
def handler0 := coreHandler policy ActorHandlerCore0.originalProgram handlerEnv0 admission0

theorem handler0ReadsState (value : Value BeamLispCore.Ty.unit) (message : Inputs) :
    (handlerEnv0 (stateSlots.put value message)).lookup (Var.succ Var.zero) = value := rfl


def handlers : List (Handler BeamLispCore.Ty.unit) := [handler0]

def recordedInputs (integers : List Int) (booleans : List Bool) : Inputs :=
  ⟨fun n => integers[n]?.getD 0, fun n => booleans[n]?.getD false⟩

def projectedFailure : Option String := some "zero-divisor"


def recordedConfig0 : Configuration BeamLispCore.Ty.unit :=
(Prod.mk Unit.unit none)

def recordedEvent1 : Event handlers :=
none

def recordedConfig1 : Configuration BeamLispCore.Ty.unit :=
(Prod.mk Unit.unit none)

def recordedHandler2 : Fin handlers.length :=
(Fin.mk 0 (by decide))

def recordedMessageValue2 : Value BeamLispCore.Ty.unit :=
Unit.unit

def recordedMessage2 : Inputs :=
(recordedInputs [] [])

def recordedEvent2 : Event handlers :=
(some (Prod.mk recordedHandler2 recordedMessage2))

def recordedConfig2 : Configuration BeamLispCore.Ty.unit :=
(Prod.mk Unit.unit projectedFailure)

def recordedEvents : List (Event handlers) :=
[recordedEvent1, recordedEvent2]

def recordedConfigurations : List (Configuration BeamLispCore.Ty.unit) :=
[recordedConfig0, recordedConfig1, recordedConfig2]

theorem recordedPrefix0 : Trace handlers policy.initial (recordedEvents.take 0) (recordedConfigurations.get ⟨0, by decide⟩) :=
  Trace.start (by rfl)

theorem recordedInvariant0 : policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 := rfl

theorem recordedSafe0 : policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 ∧ (recordedConfigurations.get ⟨0, by decide⟩).2 = none :=
  ⟨recordedInvariant0, rfl⟩

theorem recordedStep1 : Step handlers recordedConfig0 recordedEvent1 recordedConfig1 :=
  Step.idle recordedConfig0

theorem recordedPrefix1 : Trace handlers policy.initial (recordedEvents.take 1) (recordedConfigurations.get ⟨1, by decide⟩) :=
  Trace.append recordedPrefix0 recordedStep1

theorem recordedInvariant1 : policy.invariant (recordedConfigurations.get ⟨1, by decide⟩).1 := rfl

theorem recordedSafe1 : policy.invariant (recordedConfigurations.get ⟨1, by decide⟩).1 ∧ (recordedConfigurations.get ⟨1, by decide⟩).2 = none :=
  ⟨recordedInvariant1, rfl⟩

theorem recordedMessage2Read :
    (handlerEnv0 (policy.slots.put recordedConfig1.1 recordedMessage2)).lookup Var.zero =
      recordedMessageValue2 := rfl

theorem recordedStep2 : Step handlers recordedConfig1 recordedEvent2 recordedConfig2 :=
  Step.raised recordedHandler2 recordedMessage2 (by rfl) (by rfl)

theorem recordedPrefix2 : Trace handlers policy.initial (recordedEvents.take 2) (recordedConfigurations.get ⟨2, by decide⟩) :=
  Trace.append recordedPrefix1 recordedStep2

theorem recordedInvariant2 : policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 := rfl

theorem recordedUnsafePrefix : ¬ (policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 ∧ (recordedConfigurations.get ⟨2, by decide⟩).2 = none) :=
  by
  intro safe
  cases safe.2

end CoreObservedTrace

#print axioms CoreObservedTrace.handler0ReadsState
#print axioms CoreObservedTrace.recordedInvariant0
#print axioms CoreObservedTrace.recordedInvariant1
#print axioms CoreObservedTrace.recordedInvariant2
#print axioms CoreObservedTrace.recordedMessage2Read
#print axioms CoreObservedTrace.recordedPrefix0
#print axioms CoreObservedTrace.recordedPrefix1
#print axioms CoreObservedTrace.recordedPrefix2
#print axioms CoreObservedTrace.recordedSafe0
#print axioms CoreObservedTrace.recordedSafe1
#print axioms CoreObservedTrace.recordedStep1
#print axioms CoreObservedTrace.recordedStep2
#print axioms CoreObservedTrace.recordedUnsafePrefix
