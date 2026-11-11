import CoreActorCheck

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
set_option linter.unusedSimpArgs false
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop ActorTrace
set_option linter.unusedVariables false

namespace CoreObservedTrace

def recordedInputs (integers : List Int) (booleans : List Bool) : Inputs :=
  ⟨fun n => integers[n]?.getD 0, fun n => booleans[n]?.getD false⟩

def projectedFailure : Option String := some "zero-divisor"


def recordedConfig0 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit))) :=
(Prod.mk (Prod.mk (Int.ofNat 0) (Prod.mk (Int.ofNat 0) (Prod.mk (Int.ofNat 0) Unit.unit))) none)

def recordedHandler1 : Fin handlers.length :=
(Fin.mk 0 (by decide))

def recordedMessageValue1 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Int.ofNat 10) Unit.unit)

def recordedMessage1 : Inputs :=
(recordedInputs [(Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 10)] [])

def recordedEvent1 : Event handlers :=
(some (Prod.mk recordedHandler1 recordedMessage1))

def recordedConfig1 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit))) :=
(Prod.mk (Prod.mk (Int.ofNat 10) (Prod.mk (Int.ofNat 10) (Prod.mk (Int.ofNat 0) Unit.unit))) none)

def recordedHandler2 : Fin handlers.length :=
(Fin.mk 1 (by decide))

def recordedMessageValue2 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Int.ofNat 3) Unit.unit)

def recordedMessage2 : Inputs :=
(recordedInputs [(Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 3)] [])

def recordedEvent2 : Event handlers :=
(some (Prod.mk recordedHandler2 recordedMessage2))

def recordedConfig2 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit))) :=
(Prod.mk (Prod.mk (Int.ofNat 7) (Prod.mk (Int.ofNat 10) (Prod.mk (Int.ofNat 3) Unit.unit))) none)

def recordedHandler3 : Fin handlers.length :=
(Fin.mk 1 (by decide))

def recordedMessageValue3 : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Int.ofNat 100) Unit.unit)

def recordedMessage3 : Inputs :=
(recordedInputs [(Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 0), (Int.ofNat 100)] [])

def recordedEvent3 : Event handlers :=
(some (Prod.mk recordedHandler3 recordedMessage3))

def recordedConfig3 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit))) :=
(Prod.mk (Prod.mk (Int.ofNat 7) (Prod.mk (Int.ofNat 10) (Prod.mk (Int.ofNat 3) Unit.unit))) none)

def recordedEvent4 : Event handlers :=
none

def recordedConfig4 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit))) :=
(Prod.mk (Prod.mk (Int.ofNat 7) (Prod.mk (Int.ofNat 10) (Prod.mk (Int.ofNat 3) Unit.unit))) none)

def recordedEvents : List (Event handlers) :=
[recordedEvent1, recordedEvent2, recordedEvent3, recordedEvent4]

def recordedConfigurations : List (Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)))) :=
[recordedConfig0, recordedConfig1, recordedConfig2, recordedConfig3, recordedConfig4]

theorem recordedPrefix0 : Trace handlers policy.initial (recordedEvents.take 0) (recordedConfigurations.get ⟨0, by decide⟩) :=
  Trace.start (by rfl)

theorem recordedInvariant0 : policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 := rfl

theorem recordedSafe0 : policy.invariant (recordedConfigurations.get ⟨0, by decide⟩).1 ∧ (recordedConfigurations.get ⟨0, by decide⟩).2 = none :=
  originalHandlerTracesSafe recordedPrefix0

theorem recordedMessage1Read :
    (handlerEnv0 (policy.slots.put recordedConfig0.1 recordedMessage1)).lookup Var.zero =
      recordedMessageValue1 := rfl

theorem recordedStep1 : Step handlers recordedConfig0 recordedEvent1 recordedConfig1 :=
  Step.returned recordedHandler1 recordedMessage1 (by rfl) (by rfl)

theorem recordedPrefix1 : Trace handlers policy.initial (recordedEvents.take 1) (recordedConfigurations.get ⟨1, by decide⟩) :=
  Trace.append recordedPrefix0 recordedStep1

theorem recordedInvariant1 : policy.invariant (recordedConfigurations.get ⟨1, by decide⟩).1 := rfl

theorem recordedSafe1 : policy.invariant (recordedConfigurations.get ⟨1, by decide⟩).1 ∧ (recordedConfigurations.get ⟨1, by decide⟩).2 = none :=
  originalHandlerTracesSafe recordedPrefix1

theorem recordedMessage2Read :
    (handlerEnv1 (policy.slots.put recordedConfig1.1 recordedMessage2)).lookup Var.zero =
      recordedMessageValue2 := rfl

theorem recordedStep2 : Step handlers recordedConfig1 recordedEvent2 recordedConfig2 :=
  Step.returned recordedHandler2 recordedMessage2 (by rfl) (by rfl)

theorem recordedPrefix2 : Trace handlers policy.initial (recordedEvents.take 2) (recordedConfigurations.get ⟨2, by decide⟩) :=
  Trace.append recordedPrefix1 recordedStep2

theorem recordedInvariant2 : policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 := rfl

theorem recordedSafe2 : policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 ∧ (recordedConfigurations.get ⟨2, by decide⟩).2 = none :=
  originalHandlerTracesSafe recordedPrefix2

theorem recordedMessage3Read :
    (handlerEnv1 (policy.slots.put recordedConfig2.1 recordedMessage3)).lookup Var.zero =
      recordedMessageValue3 := rfl

theorem recordedStep3 : Step handlers recordedConfig2 recordedEvent3 recordedConfig3 :=
  Step.returned recordedHandler3 recordedMessage3 (by rfl) (by rfl)

theorem recordedPrefix3 : Trace handlers policy.initial (recordedEvents.take 3) (recordedConfigurations.get ⟨3, by decide⟩) :=
  Trace.append recordedPrefix2 recordedStep3

theorem recordedInvariant3 : policy.invariant (recordedConfigurations.get ⟨3, by decide⟩).1 := rfl

theorem recordedSafe3 : policy.invariant (recordedConfigurations.get ⟨3, by decide⟩).1 ∧ (recordedConfigurations.get ⟨3, by decide⟩).2 = none :=
  originalHandlerTracesSafe recordedPrefix3

theorem recordedStep4 : Step handlers recordedConfig3 recordedEvent4 recordedConfig4 :=
  Step.idle recordedConfig3

theorem recordedPrefix4 : Trace handlers policy.initial (recordedEvents.take 4) (recordedConfigurations.get ⟨4, by decide⟩) :=
  Trace.append recordedPrefix3 recordedStep4

theorem recordedInvariant4 : policy.invariant (recordedConfigurations.get ⟨4, by decide⟩).1 := rfl

theorem recordedSafe4 : policy.invariant (recordedConfigurations.get ⟨4, by decide⟩).1 ∧ (recordedConfigurations.get ⟨4, by decide⟩).2 = none :=
  originalHandlerTracesSafe recordedPrefix4

end CoreObservedTrace

#print axioms CoreObservedTrace.recordedInvariant0
#print axioms CoreObservedTrace.recordedInvariant1
#print axioms CoreObservedTrace.recordedInvariant2
#print axioms CoreObservedTrace.recordedInvariant3
#print axioms CoreObservedTrace.recordedInvariant4
#print axioms CoreObservedTrace.recordedMessage1Read
#print axioms CoreObservedTrace.recordedMessage2Read
#print axioms CoreObservedTrace.recordedMessage3Read
#print axioms CoreObservedTrace.recordedPrefix0
#print axioms CoreObservedTrace.recordedPrefix1
#print axioms CoreObservedTrace.recordedPrefix2
#print axioms CoreObservedTrace.recordedPrefix3
#print axioms CoreObservedTrace.recordedPrefix4
#print axioms CoreObservedTrace.recordedSafe0
#print axioms CoreObservedTrace.recordedSafe1
#print axioms CoreObservedTrace.recordedSafe2
#print axioms CoreObservedTrace.recordedSafe3
#print axioms CoreObservedTrace.recordedSafe4
#print axioms CoreObservedTrace.recordedStep1
#print axioms CoreObservedTrace.recordedStep2
#print axioms CoreObservedTrace.recordedStep3
#print axioms CoreObservedTrace.recordedStep4
