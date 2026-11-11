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
(Term.and (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 0)) (Term.bool true))) (Term.bool true))

def policy := StatePolicy.mk stateSlots stateIntCount stateBoolCount initialPredicate invariantPredicate


def handlers : List (Handler (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) := []

def recordedInputs (integers : List Int) (booleans : List Bool) : Inputs :=
  ⟨fun n => integers[n]?.getD 0, fun n => booleans[n]?.getD false⟩

def projectedFailure : Option String := some "zero-divisor"


def recordedConfig0 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent1 : Event handlers :=
none

def recordedConfig1 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent2 : Event handlers :=
none

def recordedConfig2 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent3 : Event handlers :=
none

def recordedConfig3 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent4 : Event handlers :=
none

def recordedConfig4 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent5 : Event handlers :=
none

def recordedConfig5 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent6 : Event handlers :=
none

def recordedConfig6 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent7 : Event handlers :=
none

def recordedConfig7 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent8 : Event handlers :=
none

def recordedConfig8 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent9 : Event handlers :=
none

def recordedConfig9 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent10 : Event handlers :=
none

def recordedConfig10 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent11 : Event handlers :=
none

def recordedConfig11 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent12 : Event handlers :=
none

def recordedConfig12 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent13 : Event handlers :=
none

def recordedConfig13 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent14 : Event handlers :=
none

def recordedConfig14 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent15 : Event handlers :=
none

def recordedConfig15 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent16 : Event handlers :=
none

def recordedConfig16 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent17 : Event handlers :=
none

def recordedConfig17 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent18 : Event handlers :=
none

def recordedConfig18 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent19 : Event handlers :=
none

def recordedConfig19 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent20 : Event handlers :=
none

def recordedConfig20 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent21 : Event handlers :=
none

def recordedConfig21 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent22 : Event handlers :=
none

def recordedConfig22 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent23 : Event handlers :=
none

def recordedConfig23 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent24 : Event handlers :=
none

def recordedConfig24 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent25 : Event handlers :=
none

def recordedConfig25 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent26 : Event handlers :=
none

def recordedConfig26 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent27 : Event handlers :=
none

def recordedConfig27 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent28 : Event handlers :=
none

def recordedConfig28 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent29 : Event handlers :=
none

def recordedConfig29 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent30 : Event handlers :=
none

def recordedConfig30 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent31 : Event handlers :=
none

def recordedConfig31 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent32 : Event handlers :=
none

def recordedConfig32 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent33 : Event handlers :=
none

def recordedConfig33 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent34 : Event handlers :=
none

def recordedConfig34 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent35 : Event handlers :=
none

def recordedConfig35 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent36 : Event handlers :=
none

def recordedConfig36 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent37 : Event handlers :=
none

def recordedConfig37 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent38 : Event handlers :=
none

def recordedConfig38 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent39 : Event handlers :=
none

def recordedConfig39 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent40 : Event handlers :=
none

def recordedConfig40 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent41 : Event handlers :=
none

def recordedConfig41 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent42 : Event handlers :=
none

def recordedConfig42 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent43 : Event handlers :=
none

def recordedConfig43 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent44 : Event handlers :=
none

def recordedConfig44 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent45 : Event handlers :=
none

def recordedConfig45 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent46 : Event handlers :=
none

def recordedConfig46 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent47 : Event handlers :=
none

def recordedConfig47 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent48 : Event handlers :=
none

def recordedConfig48 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent49 : Event handlers :=
none

def recordedConfig49 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent50 : Event handlers :=
none

def recordedConfig50 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent51 : Event handlers :=
none

def recordedConfig51 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent52 : Event handlers :=
none

def recordedConfig52 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent53 : Event handlers :=
none

def recordedConfig53 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent54 : Event handlers :=
none

def recordedConfig54 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent55 : Event handlers :=
none

def recordedConfig55 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent56 : Event handlers :=
none

def recordedConfig56 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent57 : Event handlers :=
none

def recordedConfig57 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent58 : Event handlers :=
none

def recordedConfig58 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent59 : Event handlers :=
none

def recordedConfig59 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent60 : Event handlers :=
none

def recordedConfig60 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent61 : Event handlers :=
none

def recordedConfig61 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent62 : Event handlers :=
none

def recordedConfig62 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent63 : Event handlers :=
none

def recordedConfig63 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvent64 : Event handlers :=
none

def recordedConfig64 : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit) :=
(Prod.mk (Prod.mk (Int.ofNat 0) Unit.unit) none)

def recordedEvents : List (Event handlers) :=
[recordedEvent1, recordedEvent2, recordedEvent3, recordedEvent4, recordedEvent5, recordedEvent6, recordedEvent7, recordedEvent8, recordedEvent9, recordedEvent10, recordedEvent11, recordedEvent12, recordedEvent13, recordedEvent14, recordedEvent15, recordedEvent16, recordedEvent17, recordedEvent18, recordedEvent19, recordedEvent20, recordedEvent21, recordedEvent22, recordedEvent23, recordedEvent24, recordedEvent25, recordedEvent26, recordedEvent27, recordedEvent28, recordedEvent29, recordedEvent30, recordedEvent31, recordedEvent32, recordedEvent33, recordedEvent34, recordedEvent35, recordedEvent36, recordedEvent37, recordedEvent38, recordedEvent39, recordedEvent40, recordedEvent41, recordedEvent42, recordedEvent43, recordedEvent44, recordedEvent45, recordedEvent46, recordedEvent47, recordedEvent48, recordedEvent49, recordedEvent50, recordedEvent51, recordedEvent52, recordedEvent53, recordedEvent54, recordedEvent55, recordedEvent56, recordedEvent57, recordedEvent58, recordedEvent59, recordedEvent60, recordedEvent61, recordedEvent62, recordedEvent63, recordedEvent64]

def recordedConfigurations : List (Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) :=
[recordedConfig0, recordedConfig1, recordedConfig2, recordedConfig3, recordedConfig4, recordedConfig5, recordedConfig6, recordedConfig7, recordedConfig8, recordedConfig9, recordedConfig10, recordedConfig11, recordedConfig12, recordedConfig13, recordedConfig14, recordedConfig15, recordedConfig16, recordedConfig17, recordedConfig18, recordedConfig19, recordedConfig20, recordedConfig21, recordedConfig22, recordedConfig23, recordedConfig24, recordedConfig25, recordedConfig26, recordedConfig27, recordedConfig28, recordedConfig29, recordedConfig30, recordedConfig31, recordedConfig32, recordedConfig33, recordedConfig34, recordedConfig35, recordedConfig36, recordedConfig37, recordedConfig38, recordedConfig39, recordedConfig40, recordedConfig41, recordedConfig42, recordedConfig43, recordedConfig44, recordedConfig45, recordedConfig46, recordedConfig47, recordedConfig48, recordedConfig49, recordedConfig50, recordedConfig51, recordedConfig52, recordedConfig53, recordedConfig54, recordedConfig55, recordedConfig56, recordedConfig57, recordedConfig58, recordedConfig59, recordedConfig60, recordedConfig61, recordedConfig62, recordedConfig63, recordedConfig64]

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

theorem recordedStep2 : Step handlers recordedConfig1 recordedEvent2 recordedConfig2 :=
  Step.idle recordedConfig1

theorem recordedPrefix2 : Trace handlers policy.initial (recordedEvents.take 2) (recordedConfigurations.get ⟨2, by decide⟩) :=
  Trace.append recordedPrefix1 recordedStep2

theorem recordedInvariant2 : policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 := rfl

theorem recordedSafe2 : policy.invariant (recordedConfigurations.get ⟨2, by decide⟩).1 ∧ (recordedConfigurations.get ⟨2, by decide⟩).2 = none :=
  ⟨recordedInvariant2, rfl⟩

theorem recordedStep3 : Step handlers recordedConfig2 recordedEvent3 recordedConfig3 :=
  Step.idle recordedConfig2

theorem recordedPrefix3 : Trace handlers policy.initial (recordedEvents.take 3) (recordedConfigurations.get ⟨3, by decide⟩) :=
  Trace.append recordedPrefix2 recordedStep3

theorem recordedInvariant3 : policy.invariant (recordedConfigurations.get ⟨3, by decide⟩).1 := rfl

theorem recordedSafe3 : policy.invariant (recordedConfigurations.get ⟨3, by decide⟩).1 ∧ (recordedConfigurations.get ⟨3, by decide⟩).2 = none :=
  ⟨recordedInvariant3, rfl⟩

theorem recordedStep4 : Step handlers recordedConfig3 recordedEvent4 recordedConfig4 :=
  Step.idle recordedConfig3

theorem recordedPrefix4 : Trace handlers policy.initial (recordedEvents.take 4) (recordedConfigurations.get ⟨4, by decide⟩) :=
  Trace.append recordedPrefix3 recordedStep4

theorem recordedInvariant4 : policy.invariant (recordedConfigurations.get ⟨4, by decide⟩).1 := rfl

theorem recordedSafe4 : policy.invariant (recordedConfigurations.get ⟨4, by decide⟩).1 ∧ (recordedConfigurations.get ⟨4, by decide⟩).2 = none :=
  ⟨recordedInvariant4, rfl⟩

theorem recordedStep5 : Step handlers recordedConfig4 recordedEvent5 recordedConfig5 :=
  Step.idle recordedConfig4

theorem recordedPrefix5 : Trace handlers policy.initial (recordedEvents.take 5) (recordedConfigurations.get ⟨5, by decide⟩) :=
  Trace.append recordedPrefix4 recordedStep5

theorem recordedInvariant5 : policy.invariant (recordedConfigurations.get ⟨5, by decide⟩).1 := rfl

theorem recordedSafe5 : policy.invariant (recordedConfigurations.get ⟨5, by decide⟩).1 ∧ (recordedConfigurations.get ⟨5, by decide⟩).2 = none :=
  ⟨recordedInvariant5, rfl⟩

theorem recordedStep6 : Step handlers recordedConfig5 recordedEvent6 recordedConfig6 :=
  Step.idle recordedConfig5

theorem recordedPrefix6 : Trace handlers policy.initial (recordedEvents.take 6) (recordedConfigurations.get ⟨6, by decide⟩) :=
  Trace.append recordedPrefix5 recordedStep6

theorem recordedInvariant6 : policy.invariant (recordedConfigurations.get ⟨6, by decide⟩).1 := rfl

theorem recordedSafe6 : policy.invariant (recordedConfigurations.get ⟨6, by decide⟩).1 ∧ (recordedConfigurations.get ⟨6, by decide⟩).2 = none :=
  ⟨recordedInvariant6, rfl⟩

theorem recordedStep7 : Step handlers recordedConfig6 recordedEvent7 recordedConfig7 :=
  Step.idle recordedConfig6

theorem recordedPrefix7 : Trace handlers policy.initial (recordedEvents.take 7) (recordedConfigurations.get ⟨7, by decide⟩) :=
  Trace.append recordedPrefix6 recordedStep7

theorem recordedInvariant7 : policy.invariant (recordedConfigurations.get ⟨7, by decide⟩).1 := rfl

theorem recordedSafe7 : policy.invariant (recordedConfigurations.get ⟨7, by decide⟩).1 ∧ (recordedConfigurations.get ⟨7, by decide⟩).2 = none :=
  ⟨recordedInvariant7, rfl⟩

theorem recordedStep8 : Step handlers recordedConfig7 recordedEvent8 recordedConfig8 :=
  Step.idle recordedConfig7

theorem recordedPrefix8 : Trace handlers policy.initial (recordedEvents.take 8) (recordedConfigurations.get ⟨8, by decide⟩) :=
  Trace.append recordedPrefix7 recordedStep8

theorem recordedInvariant8 : policy.invariant (recordedConfigurations.get ⟨8, by decide⟩).1 := rfl

theorem recordedSafe8 : policy.invariant (recordedConfigurations.get ⟨8, by decide⟩).1 ∧ (recordedConfigurations.get ⟨8, by decide⟩).2 = none :=
  ⟨recordedInvariant8, rfl⟩

theorem recordedStep9 : Step handlers recordedConfig8 recordedEvent9 recordedConfig9 :=
  Step.idle recordedConfig8

theorem recordedPrefix9 : Trace handlers policy.initial (recordedEvents.take 9) (recordedConfigurations.get ⟨9, by decide⟩) :=
  Trace.append recordedPrefix8 recordedStep9

theorem recordedInvariant9 : policy.invariant (recordedConfigurations.get ⟨9, by decide⟩).1 := rfl

theorem recordedSafe9 : policy.invariant (recordedConfigurations.get ⟨9, by decide⟩).1 ∧ (recordedConfigurations.get ⟨9, by decide⟩).2 = none :=
  ⟨recordedInvariant9, rfl⟩

theorem recordedStep10 : Step handlers recordedConfig9 recordedEvent10 recordedConfig10 :=
  Step.idle recordedConfig9

theorem recordedPrefix10 : Trace handlers policy.initial (recordedEvents.take 10) (recordedConfigurations.get ⟨10, by decide⟩) :=
  Trace.append recordedPrefix9 recordedStep10

theorem recordedInvariant10 : policy.invariant (recordedConfigurations.get ⟨10, by decide⟩).1 := rfl

theorem recordedSafe10 : policy.invariant (recordedConfigurations.get ⟨10, by decide⟩).1 ∧ (recordedConfigurations.get ⟨10, by decide⟩).2 = none :=
  ⟨recordedInvariant10, rfl⟩

theorem recordedStep11 : Step handlers recordedConfig10 recordedEvent11 recordedConfig11 :=
  Step.idle recordedConfig10

theorem recordedPrefix11 : Trace handlers policy.initial (recordedEvents.take 11) (recordedConfigurations.get ⟨11, by decide⟩) :=
  Trace.append recordedPrefix10 recordedStep11

theorem recordedInvariant11 : policy.invariant (recordedConfigurations.get ⟨11, by decide⟩).1 := rfl

theorem recordedSafe11 : policy.invariant (recordedConfigurations.get ⟨11, by decide⟩).1 ∧ (recordedConfigurations.get ⟨11, by decide⟩).2 = none :=
  ⟨recordedInvariant11, rfl⟩

theorem recordedStep12 : Step handlers recordedConfig11 recordedEvent12 recordedConfig12 :=
  Step.idle recordedConfig11

theorem recordedPrefix12 : Trace handlers policy.initial (recordedEvents.take 12) (recordedConfigurations.get ⟨12, by decide⟩) :=
  Trace.append recordedPrefix11 recordedStep12

theorem recordedInvariant12 : policy.invariant (recordedConfigurations.get ⟨12, by decide⟩).1 := rfl

theorem recordedSafe12 : policy.invariant (recordedConfigurations.get ⟨12, by decide⟩).1 ∧ (recordedConfigurations.get ⟨12, by decide⟩).2 = none :=
  ⟨recordedInvariant12, rfl⟩

theorem recordedStep13 : Step handlers recordedConfig12 recordedEvent13 recordedConfig13 :=
  Step.idle recordedConfig12

theorem recordedPrefix13 : Trace handlers policy.initial (recordedEvents.take 13) (recordedConfigurations.get ⟨13, by decide⟩) :=
  Trace.append recordedPrefix12 recordedStep13

theorem recordedInvariant13 : policy.invariant (recordedConfigurations.get ⟨13, by decide⟩).1 := rfl

theorem recordedSafe13 : policy.invariant (recordedConfigurations.get ⟨13, by decide⟩).1 ∧ (recordedConfigurations.get ⟨13, by decide⟩).2 = none :=
  ⟨recordedInvariant13, rfl⟩

theorem recordedStep14 : Step handlers recordedConfig13 recordedEvent14 recordedConfig14 :=
  Step.idle recordedConfig13

theorem recordedPrefix14 : Trace handlers policy.initial (recordedEvents.take 14) (recordedConfigurations.get ⟨14, by decide⟩) :=
  Trace.append recordedPrefix13 recordedStep14

theorem recordedInvariant14 : policy.invariant (recordedConfigurations.get ⟨14, by decide⟩).1 := rfl

theorem recordedSafe14 : policy.invariant (recordedConfigurations.get ⟨14, by decide⟩).1 ∧ (recordedConfigurations.get ⟨14, by decide⟩).2 = none :=
  ⟨recordedInvariant14, rfl⟩

theorem recordedStep15 : Step handlers recordedConfig14 recordedEvent15 recordedConfig15 :=
  Step.idle recordedConfig14

theorem recordedPrefix15 : Trace handlers policy.initial (recordedEvents.take 15) (recordedConfigurations.get ⟨15, by decide⟩) :=
  Trace.append recordedPrefix14 recordedStep15

theorem recordedInvariant15 : policy.invariant (recordedConfigurations.get ⟨15, by decide⟩).1 := rfl

theorem recordedSafe15 : policy.invariant (recordedConfigurations.get ⟨15, by decide⟩).1 ∧ (recordedConfigurations.get ⟨15, by decide⟩).2 = none :=
  ⟨recordedInvariant15, rfl⟩

theorem recordedStep16 : Step handlers recordedConfig15 recordedEvent16 recordedConfig16 :=
  Step.idle recordedConfig15

theorem recordedPrefix16 : Trace handlers policy.initial (recordedEvents.take 16) (recordedConfigurations.get ⟨16, by decide⟩) :=
  Trace.append recordedPrefix15 recordedStep16

theorem recordedInvariant16 : policy.invariant (recordedConfigurations.get ⟨16, by decide⟩).1 := rfl

theorem recordedSafe16 : policy.invariant (recordedConfigurations.get ⟨16, by decide⟩).1 ∧ (recordedConfigurations.get ⟨16, by decide⟩).2 = none :=
  ⟨recordedInvariant16, rfl⟩

theorem recordedStep17 : Step handlers recordedConfig16 recordedEvent17 recordedConfig17 :=
  Step.idle recordedConfig16

theorem recordedPrefix17 : Trace handlers policy.initial (recordedEvents.take 17) (recordedConfigurations.get ⟨17, by decide⟩) :=
  Trace.append recordedPrefix16 recordedStep17

theorem recordedInvariant17 : policy.invariant (recordedConfigurations.get ⟨17, by decide⟩).1 := rfl

theorem recordedSafe17 : policy.invariant (recordedConfigurations.get ⟨17, by decide⟩).1 ∧ (recordedConfigurations.get ⟨17, by decide⟩).2 = none :=
  ⟨recordedInvariant17, rfl⟩

theorem recordedStep18 : Step handlers recordedConfig17 recordedEvent18 recordedConfig18 :=
  Step.idle recordedConfig17

theorem recordedPrefix18 : Trace handlers policy.initial (recordedEvents.take 18) (recordedConfigurations.get ⟨18, by decide⟩) :=
  Trace.append recordedPrefix17 recordedStep18

theorem recordedInvariant18 : policy.invariant (recordedConfigurations.get ⟨18, by decide⟩).1 := rfl

theorem recordedSafe18 : policy.invariant (recordedConfigurations.get ⟨18, by decide⟩).1 ∧ (recordedConfigurations.get ⟨18, by decide⟩).2 = none :=
  ⟨recordedInvariant18, rfl⟩

theorem recordedStep19 : Step handlers recordedConfig18 recordedEvent19 recordedConfig19 :=
  Step.idle recordedConfig18

theorem recordedPrefix19 : Trace handlers policy.initial (recordedEvents.take 19) (recordedConfigurations.get ⟨19, by decide⟩) :=
  Trace.append recordedPrefix18 recordedStep19

theorem recordedInvariant19 : policy.invariant (recordedConfigurations.get ⟨19, by decide⟩).1 := rfl

theorem recordedSafe19 : policy.invariant (recordedConfigurations.get ⟨19, by decide⟩).1 ∧ (recordedConfigurations.get ⟨19, by decide⟩).2 = none :=
  ⟨recordedInvariant19, rfl⟩

theorem recordedStep20 : Step handlers recordedConfig19 recordedEvent20 recordedConfig20 :=
  Step.idle recordedConfig19

theorem recordedPrefix20 : Trace handlers policy.initial (recordedEvents.take 20) (recordedConfigurations.get ⟨20, by decide⟩) :=
  Trace.append recordedPrefix19 recordedStep20

theorem recordedInvariant20 : policy.invariant (recordedConfigurations.get ⟨20, by decide⟩).1 := rfl

theorem recordedSafe20 : policy.invariant (recordedConfigurations.get ⟨20, by decide⟩).1 ∧ (recordedConfigurations.get ⟨20, by decide⟩).2 = none :=
  ⟨recordedInvariant20, rfl⟩

theorem recordedStep21 : Step handlers recordedConfig20 recordedEvent21 recordedConfig21 :=
  Step.idle recordedConfig20

theorem recordedPrefix21 : Trace handlers policy.initial (recordedEvents.take 21) (recordedConfigurations.get ⟨21, by decide⟩) :=
  Trace.append recordedPrefix20 recordedStep21

theorem recordedInvariant21 : policy.invariant (recordedConfigurations.get ⟨21, by decide⟩).1 := rfl

theorem recordedSafe21 : policy.invariant (recordedConfigurations.get ⟨21, by decide⟩).1 ∧ (recordedConfigurations.get ⟨21, by decide⟩).2 = none :=
  ⟨recordedInvariant21, rfl⟩

theorem recordedStep22 : Step handlers recordedConfig21 recordedEvent22 recordedConfig22 :=
  Step.idle recordedConfig21

theorem recordedPrefix22 : Trace handlers policy.initial (recordedEvents.take 22) (recordedConfigurations.get ⟨22, by decide⟩) :=
  Trace.append recordedPrefix21 recordedStep22

theorem recordedInvariant22 : policy.invariant (recordedConfigurations.get ⟨22, by decide⟩).1 := rfl

theorem recordedSafe22 : policy.invariant (recordedConfigurations.get ⟨22, by decide⟩).1 ∧ (recordedConfigurations.get ⟨22, by decide⟩).2 = none :=
  ⟨recordedInvariant22, rfl⟩

theorem recordedStep23 : Step handlers recordedConfig22 recordedEvent23 recordedConfig23 :=
  Step.idle recordedConfig22

theorem recordedPrefix23 : Trace handlers policy.initial (recordedEvents.take 23) (recordedConfigurations.get ⟨23, by decide⟩) :=
  Trace.append recordedPrefix22 recordedStep23

theorem recordedInvariant23 : policy.invariant (recordedConfigurations.get ⟨23, by decide⟩).1 := rfl

theorem recordedSafe23 : policy.invariant (recordedConfigurations.get ⟨23, by decide⟩).1 ∧ (recordedConfigurations.get ⟨23, by decide⟩).2 = none :=
  ⟨recordedInvariant23, rfl⟩

theorem recordedStep24 : Step handlers recordedConfig23 recordedEvent24 recordedConfig24 :=
  Step.idle recordedConfig23

theorem recordedPrefix24 : Trace handlers policy.initial (recordedEvents.take 24) (recordedConfigurations.get ⟨24, by decide⟩) :=
  Trace.append recordedPrefix23 recordedStep24

theorem recordedInvariant24 : policy.invariant (recordedConfigurations.get ⟨24, by decide⟩).1 := rfl

theorem recordedSafe24 : policy.invariant (recordedConfigurations.get ⟨24, by decide⟩).1 ∧ (recordedConfigurations.get ⟨24, by decide⟩).2 = none :=
  ⟨recordedInvariant24, rfl⟩

theorem recordedStep25 : Step handlers recordedConfig24 recordedEvent25 recordedConfig25 :=
  Step.idle recordedConfig24

theorem recordedPrefix25 : Trace handlers policy.initial (recordedEvents.take 25) (recordedConfigurations.get ⟨25, by decide⟩) :=
  Trace.append recordedPrefix24 recordedStep25

theorem recordedInvariant25 : policy.invariant (recordedConfigurations.get ⟨25, by decide⟩).1 := rfl

theorem recordedSafe25 : policy.invariant (recordedConfigurations.get ⟨25, by decide⟩).1 ∧ (recordedConfigurations.get ⟨25, by decide⟩).2 = none :=
  ⟨recordedInvariant25, rfl⟩

theorem recordedStep26 : Step handlers recordedConfig25 recordedEvent26 recordedConfig26 :=
  Step.idle recordedConfig25

theorem recordedPrefix26 : Trace handlers policy.initial (recordedEvents.take 26) (recordedConfigurations.get ⟨26, by decide⟩) :=
  Trace.append recordedPrefix25 recordedStep26

theorem recordedInvariant26 : policy.invariant (recordedConfigurations.get ⟨26, by decide⟩).1 := rfl

theorem recordedSafe26 : policy.invariant (recordedConfigurations.get ⟨26, by decide⟩).1 ∧ (recordedConfigurations.get ⟨26, by decide⟩).2 = none :=
  ⟨recordedInvariant26, rfl⟩

theorem recordedStep27 : Step handlers recordedConfig26 recordedEvent27 recordedConfig27 :=
  Step.idle recordedConfig26

theorem recordedPrefix27 : Trace handlers policy.initial (recordedEvents.take 27) (recordedConfigurations.get ⟨27, by decide⟩) :=
  Trace.append recordedPrefix26 recordedStep27

theorem recordedInvariant27 : policy.invariant (recordedConfigurations.get ⟨27, by decide⟩).1 := rfl

theorem recordedSafe27 : policy.invariant (recordedConfigurations.get ⟨27, by decide⟩).1 ∧ (recordedConfigurations.get ⟨27, by decide⟩).2 = none :=
  ⟨recordedInvariant27, rfl⟩

theorem recordedStep28 : Step handlers recordedConfig27 recordedEvent28 recordedConfig28 :=
  Step.idle recordedConfig27

theorem recordedPrefix28 : Trace handlers policy.initial (recordedEvents.take 28) (recordedConfigurations.get ⟨28, by decide⟩) :=
  Trace.append recordedPrefix27 recordedStep28

theorem recordedInvariant28 : policy.invariant (recordedConfigurations.get ⟨28, by decide⟩).1 := rfl

theorem recordedSafe28 : policy.invariant (recordedConfigurations.get ⟨28, by decide⟩).1 ∧ (recordedConfigurations.get ⟨28, by decide⟩).2 = none :=
  ⟨recordedInvariant28, rfl⟩

theorem recordedStep29 : Step handlers recordedConfig28 recordedEvent29 recordedConfig29 :=
  Step.idle recordedConfig28

theorem recordedPrefix29 : Trace handlers policy.initial (recordedEvents.take 29) (recordedConfigurations.get ⟨29, by decide⟩) :=
  Trace.append recordedPrefix28 recordedStep29

theorem recordedInvariant29 : policy.invariant (recordedConfigurations.get ⟨29, by decide⟩).1 := rfl

theorem recordedSafe29 : policy.invariant (recordedConfigurations.get ⟨29, by decide⟩).1 ∧ (recordedConfigurations.get ⟨29, by decide⟩).2 = none :=
  ⟨recordedInvariant29, rfl⟩

theorem recordedStep30 : Step handlers recordedConfig29 recordedEvent30 recordedConfig30 :=
  Step.idle recordedConfig29

theorem recordedPrefix30 : Trace handlers policy.initial (recordedEvents.take 30) (recordedConfigurations.get ⟨30, by decide⟩) :=
  Trace.append recordedPrefix29 recordedStep30

theorem recordedInvariant30 : policy.invariant (recordedConfigurations.get ⟨30, by decide⟩).1 := rfl

theorem recordedSafe30 : policy.invariant (recordedConfigurations.get ⟨30, by decide⟩).1 ∧ (recordedConfigurations.get ⟨30, by decide⟩).2 = none :=
  ⟨recordedInvariant30, rfl⟩

theorem recordedStep31 : Step handlers recordedConfig30 recordedEvent31 recordedConfig31 :=
  Step.idle recordedConfig30

theorem recordedPrefix31 : Trace handlers policy.initial (recordedEvents.take 31) (recordedConfigurations.get ⟨31, by decide⟩) :=
  Trace.append recordedPrefix30 recordedStep31

theorem recordedInvariant31 : policy.invariant (recordedConfigurations.get ⟨31, by decide⟩).1 := rfl

theorem recordedSafe31 : policy.invariant (recordedConfigurations.get ⟨31, by decide⟩).1 ∧ (recordedConfigurations.get ⟨31, by decide⟩).2 = none :=
  ⟨recordedInvariant31, rfl⟩

theorem recordedStep32 : Step handlers recordedConfig31 recordedEvent32 recordedConfig32 :=
  Step.idle recordedConfig31

theorem recordedPrefix32 : Trace handlers policy.initial (recordedEvents.take 32) (recordedConfigurations.get ⟨32, by decide⟩) :=
  Trace.append recordedPrefix31 recordedStep32

theorem recordedInvariant32 : policy.invariant (recordedConfigurations.get ⟨32, by decide⟩).1 := rfl

theorem recordedSafe32 : policy.invariant (recordedConfigurations.get ⟨32, by decide⟩).1 ∧ (recordedConfigurations.get ⟨32, by decide⟩).2 = none :=
  ⟨recordedInvariant32, rfl⟩

theorem recordedStep33 : Step handlers recordedConfig32 recordedEvent33 recordedConfig33 :=
  Step.idle recordedConfig32

theorem recordedPrefix33 : Trace handlers policy.initial (recordedEvents.take 33) (recordedConfigurations.get ⟨33, by decide⟩) :=
  Trace.append recordedPrefix32 recordedStep33

theorem recordedInvariant33 : policy.invariant (recordedConfigurations.get ⟨33, by decide⟩).1 := rfl

theorem recordedSafe33 : policy.invariant (recordedConfigurations.get ⟨33, by decide⟩).1 ∧ (recordedConfigurations.get ⟨33, by decide⟩).2 = none :=
  ⟨recordedInvariant33, rfl⟩

theorem recordedStep34 : Step handlers recordedConfig33 recordedEvent34 recordedConfig34 :=
  Step.idle recordedConfig33

theorem recordedPrefix34 : Trace handlers policy.initial (recordedEvents.take 34) (recordedConfigurations.get ⟨34, by decide⟩) :=
  Trace.append recordedPrefix33 recordedStep34

theorem recordedInvariant34 : policy.invariant (recordedConfigurations.get ⟨34, by decide⟩).1 := rfl

theorem recordedSafe34 : policy.invariant (recordedConfigurations.get ⟨34, by decide⟩).1 ∧ (recordedConfigurations.get ⟨34, by decide⟩).2 = none :=
  ⟨recordedInvariant34, rfl⟩

theorem recordedStep35 : Step handlers recordedConfig34 recordedEvent35 recordedConfig35 :=
  Step.idle recordedConfig34

theorem recordedPrefix35 : Trace handlers policy.initial (recordedEvents.take 35) (recordedConfigurations.get ⟨35, by decide⟩) :=
  Trace.append recordedPrefix34 recordedStep35

theorem recordedInvariant35 : policy.invariant (recordedConfigurations.get ⟨35, by decide⟩).1 := rfl

theorem recordedSafe35 : policy.invariant (recordedConfigurations.get ⟨35, by decide⟩).1 ∧ (recordedConfigurations.get ⟨35, by decide⟩).2 = none :=
  ⟨recordedInvariant35, rfl⟩

theorem recordedStep36 : Step handlers recordedConfig35 recordedEvent36 recordedConfig36 :=
  Step.idle recordedConfig35

theorem recordedPrefix36 : Trace handlers policy.initial (recordedEvents.take 36) (recordedConfigurations.get ⟨36, by decide⟩) :=
  Trace.append recordedPrefix35 recordedStep36

theorem recordedInvariant36 : policy.invariant (recordedConfigurations.get ⟨36, by decide⟩).1 := rfl

theorem recordedSafe36 : policy.invariant (recordedConfigurations.get ⟨36, by decide⟩).1 ∧ (recordedConfigurations.get ⟨36, by decide⟩).2 = none :=
  ⟨recordedInvariant36, rfl⟩

theorem recordedStep37 : Step handlers recordedConfig36 recordedEvent37 recordedConfig37 :=
  Step.idle recordedConfig36

theorem recordedPrefix37 : Trace handlers policy.initial (recordedEvents.take 37) (recordedConfigurations.get ⟨37, by decide⟩) :=
  Trace.append recordedPrefix36 recordedStep37

theorem recordedInvariant37 : policy.invariant (recordedConfigurations.get ⟨37, by decide⟩).1 := rfl

theorem recordedSafe37 : policy.invariant (recordedConfigurations.get ⟨37, by decide⟩).1 ∧ (recordedConfigurations.get ⟨37, by decide⟩).2 = none :=
  ⟨recordedInvariant37, rfl⟩

theorem recordedStep38 : Step handlers recordedConfig37 recordedEvent38 recordedConfig38 :=
  Step.idle recordedConfig37

theorem recordedPrefix38 : Trace handlers policy.initial (recordedEvents.take 38) (recordedConfigurations.get ⟨38, by decide⟩) :=
  Trace.append recordedPrefix37 recordedStep38

theorem recordedInvariant38 : policy.invariant (recordedConfigurations.get ⟨38, by decide⟩).1 := rfl

theorem recordedSafe38 : policy.invariant (recordedConfigurations.get ⟨38, by decide⟩).1 ∧ (recordedConfigurations.get ⟨38, by decide⟩).2 = none :=
  ⟨recordedInvariant38, rfl⟩

theorem recordedStep39 : Step handlers recordedConfig38 recordedEvent39 recordedConfig39 :=
  Step.idle recordedConfig38

theorem recordedPrefix39 : Trace handlers policy.initial (recordedEvents.take 39) (recordedConfigurations.get ⟨39, by decide⟩) :=
  Trace.append recordedPrefix38 recordedStep39

theorem recordedInvariant39 : policy.invariant (recordedConfigurations.get ⟨39, by decide⟩).1 := rfl

theorem recordedSafe39 : policy.invariant (recordedConfigurations.get ⟨39, by decide⟩).1 ∧ (recordedConfigurations.get ⟨39, by decide⟩).2 = none :=
  ⟨recordedInvariant39, rfl⟩

theorem recordedStep40 : Step handlers recordedConfig39 recordedEvent40 recordedConfig40 :=
  Step.idle recordedConfig39

theorem recordedPrefix40 : Trace handlers policy.initial (recordedEvents.take 40) (recordedConfigurations.get ⟨40, by decide⟩) :=
  Trace.append recordedPrefix39 recordedStep40

theorem recordedInvariant40 : policy.invariant (recordedConfigurations.get ⟨40, by decide⟩).1 := rfl

theorem recordedSafe40 : policy.invariant (recordedConfigurations.get ⟨40, by decide⟩).1 ∧ (recordedConfigurations.get ⟨40, by decide⟩).2 = none :=
  ⟨recordedInvariant40, rfl⟩

theorem recordedStep41 : Step handlers recordedConfig40 recordedEvent41 recordedConfig41 :=
  Step.idle recordedConfig40

theorem recordedPrefix41 : Trace handlers policy.initial (recordedEvents.take 41) (recordedConfigurations.get ⟨41, by decide⟩) :=
  Trace.append recordedPrefix40 recordedStep41

theorem recordedInvariant41 : policy.invariant (recordedConfigurations.get ⟨41, by decide⟩).1 := rfl

theorem recordedSafe41 : policy.invariant (recordedConfigurations.get ⟨41, by decide⟩).1 ∧ (recordedConfigurations.get ⟨41, by decide⟩).2 = none :=
  ⟨recordedInvariant41, rfl⟩

theorem recordedStep42 : Step handlers recordedConfig41 recordedEvent42 recordedConfig42 :=
  Step.idle recordedConfig41

theorem recordedPrefix42 : Trace handlers policy.initial (recordedEvents.take 42) (recordedConfigurations.get ⟨42, by decide⟩) :=
  Trace.append recordedPrefix41 recordedStep42

theorem recordedInvariant42 : policy.invariant (recordedConfigurations.get ⟨42, by decide⟩).1 := rfl

theorem recordedSafe42 : policy.invariant (recordedConfigurations.get ⟨42, by decide⟩).1 ∧ (recordedConfigurations.get ⟨42, by decide⟩).2 = none :=
  ⟨recordedInvariant42, rfl⟩

theorem recordedStep43 : Step handlers recordedConfig42 recordedEvent43 recordedConfig43 :=
  Step.idle recordedConfig42

theorem recordedPrefix43 : Trace handlers policy.initial (recordedEvents.take 43) (recordedConfigurations.get ⟨43, by decide⟩) :=
  Trace.append recordedPrefix42 recordedStep43

theorem recordedInvariant43 : policy.invariant (recordedConfigurations.get ⟨43, by decide⟩).1 := rfl

theorem recordedSafe43 : policy.invariant (recordedConfigurations.get ⟨43, by decide⟩).1 ∧ (recordedConfigurations.get ⟨43, by decide⟩).2 = none :=
  ⟨recordedInvariant43, rfl⟩

theorem recordedStep44 : Step handlers recordedConfig43 recordedEvent44 recordedConfig44 :=
  Step.idle recordedConfig43

theorem recordedPrefix44 : Trace handlers policy.initial (recordedEvents.take 44) (recordedConfigurations.get ⟨44, by decide⟩) :=
  Trace.append recordedPrefix43 recordedStep44

theorem recordedInvariant44 : policy.invariant (recordedConfigurations.get ⟨44, by decide⟩).1 := rfl

theorem recordedSafe44 : policy.invariant (recordedConfigurations.get ⟨44, by decide⟩).1 ∧ (recordedConfigurations.get ⟨44, by decide⟩).2 = none :=
  ⟨recordedInvariant44, rfl⟩

theorem recordedStep45 : Step handlers recordedConfig44 recordedEvent45 recordedConfig45 :=
  Step.idle recordedConfig44

theorem recordedPrefix45 : Trace handlers policy.initial (recordedEvents.take 45) (recordedConfigurations.get ⟨45, by decide⟩) :=
  Trace.append recordedPrefix44 recordedStep45

theorem recordedInvariant45 : policy.invariant (recordedConfigurations.get ⟨45, by decide⟩).1 := rfl

theorem recordedSafe45 : policy.invariant (recordedConfigurations.get ⟨45, by decide⟩).1 ∧ (recordedConfigurations.get ⟨45, by decide⟩).2 = none :=
  ⟨recordedInvariant45, rfl⟩

theorem recordedStep46 : Step handlers recordedConfig45 recordedEvent46 recordedConfig46 :=
  Step.idle recordedConfig45

theorem recordedPrefix46 : Trace handlers policy.initial (recordedEvents.take 46) (recordedConfigurations.get ⟨46, by decide⟩) :=
  Trace.append recordedPrefix45 recordedStep46

theorem recordedInvariant46 : policy.invariant (recordedConfigurations.get ⟨46, by decide⟩).1 := rfl

theorem recordedSafe46 : policy.invariant (recordedConfigurations.get ⟨46, by decide⟩).1 ∧ (recordedConfigurations.get ⟨46, by decide⟩).2 = none :=
  ⟨recordedInvariant46, rfl⟩

theorem recordedStep47 : Step handlers recordedConfig46 recordedEvent47 recordedConfig47 :=
  Step.idle recordedConfig46

theorem recordedPrefix47 : Trace handlers policy.initial (recordedEvents.take 47) (recordedConfigurations.get ⟨47, by decide⟩) :=
  Trace.append recordedPrefix46 recordedStep47

theorem recordedInvariant47 : policy.invariant (recordedConfigurations.get ⟨47, by decide⟩).1 := rfl

theorem recordedSafe47 : policy.invariant (recordedConfigurations.get ⟨47, by decide⟩).1 ∧ (recordedConfigurations.get ⟨47, by decide⟩).2 = none :=
  ⟨recordedInvariant47, rfl⟩

theorem recordedStep48 : Step handlers recordedConfig47 recordedEvent48 recordedConfig48 :=
  Step.idle recordedConfig47

theorem recordedPrefix48 : Trace handlers policy.initial (recordedEvents.take 48) (recordedConfigurations.get ⟨48, by decide⟩) :=
  Trace.append recordedPrefix47 recordedStep48

theorem recordedInvariant48 : policy.invariant (recordedConfigurations.get ⟨48, by decide⟩).1 := rfl

theorem recordedSafe48 : policy.invariant (recordedConfigurations.get ⟨48, by decide⟩).1 ∧ (recordedConfigurations.get ⟨48, by decide⟩).2 = none :=
  ⟨recordedInvariant48, rfl⟩

theorem recordedStep49 : Step handlers recordedConfig48 recordedEvent49 recordedConfig49 :=
  Step.idle recordedConfig48

theorem recordedPrefix49 : Trace handlers policy.initial (recordedEvents.take 49) (recordedConfigurations.get ⟨49, by decide⟩) :=
  Trace.append recordedPrefix48 recordedStep49

theorem recordedInvariant49 : policy.invariant (recordedConfigurations.get ⟨49, by decide⟩).1 := rfl

theorem recordedSafe49 : policy.invariant (recordedConfigurations.get ⟨49, by decide⟩).1 ∧ (recordedConfigurations.get ⟨49, by decide⟩).2 = none :=
  ⟨recordedInvariant49, rfl⟩

theorem recordedStep50 : Step handlers recordedConfig49 recordedEvent50 recordedConfig50 :=
  Step.idle recordedConfig49

theorem recordedPrefix50 : Trace handlers policy.initial (recordedEvents.take 50) (recordedConfigurations.get ⟨50, by decide⟩) :=
  Trace.append recordedPrefix49 recordedStep50

theorem recordedInvariant50 : policy.invariant (recordedConfigurations.get ⟨50, by decide⟩).1 := rfl

theorem recordedSafe50 : policy.invariant (recordedConfigurations.get ⟨50, by decide⟩).1 ∧ (recordedConfigurations.get ⟨50, by decide⟩).2 = none :=
  ⟨recordedInvariant50, rfl⟩

theorem recordedStep51 : Step handlers recordedConfig50 recordedEvent51 recordedConfig51 :=
  Step.idle recordedConfig50

theorem recordedPrefix51 : Trace handlers policy.initial (recordedEvents.take 51) (recordedConfigurations.get ⟨51, by decide⟩) :=
  Trace.append recordedPrefix50 recordedStep51

theorem recordedInvariant51 : policy.invariant (recordedConfigurations.get ⟨51, by decide⟩).1 := rfl

theorem recordedSafe51 : policy.invariant (recordedConfigurations.get ⟨51, by decide⟩).1 ∧ (recordedConfigurations.get ⟨51, by decide⟩).2 = none :=
  ⟨recordedInvariant51, rfl⟩

theorem recordedStep52 : Step handlers recordedConfig51 recordedEvent52 recordedConfig52 :=
  Step.idle recordedConfig51

theorem recordedPrefix52 : Trace handlers policy.initial (recordedEvents.take 52) (recordedConfigurations.get ⟨52, by decide⟩) :=
  Trace.append recordedPrefix51 recordedStep52

theorem recordedInvariant52 : policy.invariant (recordedConfigurations.get ⟨52, by decide⟩).1 := rfl

theorem recordedSafe52 : policy.invariant (recordedConfigurations.get ⟨52, by decide⟩).1 ∧ (recordedConfigurations.get ⟨52, by decide⟩).2 = none :=
  ⟨recordedInvariant52, rfl⟩

theorem recordedStep53 : Step handlers recordedConfig52 recordedEvent53 recordedConfig53 :=
  Step.idle recordedConfig52

theorem recordedPrefix53 : Trace handlers policy.initial (recordedEvents.take 53) (recordedConfigurations.get ⟨53, by decide⟩) :=
  Trace.append recordedPrefix52 recordedStep53

theorem recordedInvariant53 : policy.invariant (recordedConfigurations.get ⟨53, by decide⟩).1 := rfl

theorem recordedSafe53 : policy.invariant (recordedConfigurations.get ⟨53, by decide⟩).1 ∧ (recordedConfigurations.get ⟨53, by decide⟩).2 = none :=
  ⟨recordedInvariant53, rfl⟩

theorem recordedStep54 : Step handlers recordedConfig53 recordedEvent54 recordedConfig54 :=
  Step.idle recordedConfig53

theorem recordedPrefix54 : Trace handlers policy.initial (recordedEvents.take 54) (recordedConfigurations.get ⟨54, by decide⟩) :=
  Trace.append recordedPrefix53 recordedStep54

theorem recordedInvariant54 : policy.invariant (recordedConfigurations.get ⟨54, by decide⟩).1 := rfl

theorem recordedSafe54 : policy.invariant (recordedConfigurations.get ⟨54, by decide⟩).1 ∧ (recordedConfigurations.get ⟨54, by decide⟩).2 = none :=
  ⟨recordedInvariant54, rfl⟩

theorem recordedStep55 : Step handlers recordedConfig54 recordedEvent55 recordedConfig55 :=
  Step.idle recordedConfig54

theorem recordedPrefix55 : Trace handlers policy.initial (recordedEvents.take 55) (recordedConfigurations.get ⟨55, by decide⟩) :=
  Trace.append recordedPrefix54 recordedStep55

theorem recordedInvariant55 : policy.invariant (recordedConfigurations.get ⟨55, by decide⟩).1 := rfl

theorem recordedSafe55 : policy.invariant (recordedConfigurations.get ⟨55, by decide⟩).1 ∧ (recordedConfigurations.get ⟨55, by decide⟩).2 = none :=
  ⟨recordedInvariant55, rfl⟩

theorem recordedStep56 : Step handlers recordedConfig55 recordedEvent56 recordedConfig56 :=
  Step.idle recordedConfig55

theorem recordedPrefix56 : Trace handlers policy.initial (recordedEvents.take 56) (recordedConfigurations.get ⟨56, by decide⟩) :=
  Trace.append recordedPrefix55 recordedStep56

theorem recordedInvariant56 : policy.invariant (recordedConfigurations.get ⟨56, by decide⟩).1 := rfl

theorem recordedSafe56 : policy.invariant (recordedConfigurations.get ⟨56, by decide⟩).1 ∧ (recordedConfigurations.get ⟨56, by decide⟩).2 = none :=
  ⟨recordedInvariant56, rfl⟩

theorem recordedStep57 : Step handlers recordedConfig56 recordedEvent57 recordedConfig57 :=
  Step.idle recordedConfig56

theorem recordedPrefix57 : Trace handlers policy.initial (recordedEvents.take 57) (recordedConfigurations.get ⟨57, by decide⟩) :=
  Trace.append recordedPrefix56 recordedStep57

theorem recordedInvariant57 : policy.invariant (recordedConfigurations.get ⟨57, by decide⟩).1 := rfl

theorem recordedSafe57 : policy.invariant (recordedConfigurations.get ⟨57, by decide⟩).1 ∧ (recordedConfigurations.get ⟨57, by decide⟩).2 = none :=
  ⟨recordedInvariant57, rfl⟩

theorem recordedStep58 : Step handlers recordedConfig57 recordedEvent58 recordedConfig58 :=
  Step.idle recordedConfig57

theorem recordedPrefix58 : Trace handlers policy.initial (recordedEvents.take 58) (recordedConfigurations.get ⟨58, by decide⟩) :=
  Trace.append recordedPrefix57 recordedStep58

theorem recordedInvariant58 : policy.invariant (recordedConfigurations.get ⟨58, by decide⟩).1 := rfl

theorem recordedSafe58 : policy.invariant (recordedConfigurations.get ⟨58, by decide⟩).1 ∧ (recordedConfigurations.get ⟨58, by decide⟩).2 = none :=
  ⟨recordedInvariant58, rfl⟩

theorem recordedStep59 : Step handlers recordedConfig58 recordedEvent59 recordedConfig59 :=
  Step.idle recordedConfig58

theorem recordedPrefix59 : Trace handlers policy.initial (recordedEvents.take 59) (recordedConfigurations.get ⟨59, by decide⟩) :=
  Trace.append recordedPrefix58 recordedStep59

theorem recordedInvariant59 : policy.invariant (recordedConfigurations.get ⟨59, by decide⟩).1 := rfl

theorem recordedSafe59 : policy.invariant (recordedConfigurations.get ⟨59, by decide⟩).1 ∧ (recordedConfigurations.get ⟨59, by decide⟩).2 = none :=
  ⟨recordedInvariant59, rfl⟩

theorem recordedStep60 : Step handlers recordedConfig59 recordedEvent60 recordedConfig60 :=
  Step.idle recordedConfig59

theorem recordedPrefix60 : Trace handlers policy.initial (recordedEvents.take 60) (recordedConfigurations.get ⟨60, by decide⟩) :=
  Trace.append recordedPrefix59 recordedStep60

theorem recordedInvariant60 : policy.invariant (recordedConfigurations.get ⟨60, by decide⟩).1 := rfl

theorem recordedSafe60 : policy.invariant (recordedConfigurations.get ⟨60, by decide⟩).1 ∧ (recordedConfigurations.get ⟨60, by decide⟩).2 = none :=
  ⟨recordedInvariant60, rfl⟩

theorem recordedStep61 : Step handlers recordedConfig60 recordedEvent61 recordedConfig61 :=
  Step.idle recordedConfig60

theorem recordedPrefix61 : Trace handlers policy.initial (recordedEvents.take 61) (recordedConfigurations.get ⟨61, by decide⟩) :=
  Trace.append recordedPrefix60 recordedStep61

theorem recordedInvariant61 : policy.invariant (recordedConfigurations.get ⟨61, by decide⟩).1 := rfl

theorem recordedSafe61 : policy.invariant (recordedConfigurations.get ⟨61, by decide⟩).1 ∧ (recordedConfigurations.get ⟨61, by decide⟩).2 = none :=
  ⟨recordedInvariant61, rfl⟩

theorem recordedStep62 : Step handlers recordedConfig61 recordedEvent62 recordedConfig62 :=
  Step.idle recordedConfig61

theorem recordedPrefix62 : Trace handlers policy.initial (recordedEvents.take 62) (recordedConfigurations.get ⟨62, by decide⟩) :=
  Trace.append recordedPrefix61 recordedStep62

theorem recordedInvariant62 : policy.invariant (recordedConfigurations.get ⟨62, by decide⟩).1 := rfl

theorem recordedSafe62 : policy.invariant (recordedConfigurations.get ⟨62, by decide⟩).1 ∧ (recordedConfigurations.get ⟨62, by decide⟩).2 = none :=
  ⟨recordedInvariant62, rfl⟩

theorem recordedStep63 : Step handlers recordedConfig62 recordedEvent63 recordedConfig63 :=
  Step.idle recordedConfig62

theorem recordedPrefix63 : Trace handlers policy.initial (recordedEvents.take 63) (recordedConfigurations.get ⟨63, by decide⟩) :=
  Trace.append recordedPrefix62 recordedStep63

theorem recordedInvariant63 : policy.invariant (recordedConfigurations.get ⟨63, by decide⟩).1 := rfl

theorem recordedSafe63 : policy.invariant (recordedConfigurations.get ⟨63, by decide⟩).1 ∧ (recordedConfigurations.get ⟨63, by decide⟩).2 = none :=
  ⟨recordedInvariant63, rfl⟩

theorem recordedStep64 : Step handlers recordedConfig63 recordedEvent64 recordedConfig64 :=
  Step.idle recordedConfig63

theorem recordedPrefix64 : Trace handlers policy.initial (recordedEvents.take 64) (recordedConfigurations.get ⟨64, by decide⟩) :=
  Trace.append recordedPrefix63 recordedStep64

theorem recordedInvariant64 : policy.invariant (recordedConfigurations.get ⟨64, by decide⟩).1 := rfl

theorem recordedSafe64 : policy.invariant (recordedConfigurations.get ⟨64, by decide⟩).1 ∧ (recordedConfigurations.get ⟨64, by decide⟩).2 = none :=
  ⟨recordedInvariant64, rfl⟩

end CoreObservedTrace

#print axioms CoreObservedTrace.recordedInvariant0
#print axioms CoreObservedTrace.recordedInvariant1
#print axioms CoreObservedTrace.recordedInvariant10
#print axioms CoreObservedTrace.recordedInvariant11
#print axioms CoreObservedTrace.recordedInvariant12
#print axioms CoreObservedTrace.recordedInvariant13
#print axioms CoreObservedTrace.recordedInvariant14
#print axioms CoreObservedTrace.recordedInvariant15
#print axioms CoreObservedTrace.recordedInvariant16
#print axioms CoreObservedTrace.recordedInvariant17
#print axioms CoreObservedTrace.recordedInvariant18
#print axioms CoreObservedTrace.recordedInvariant19
#print axioms CoreObservedTrace.recordedInvariant2
#print axioms CoreObservedTrace.recordedInvariant20
#print axioms CoreObservedTrace.recordedInvariant21
#print axioms CoreObservedTrace.recordedInvariant22
#print axioms CoreObservedTrace.recordedInvariant23
#print axioms CoreObservedTrace.recordedInvariant24
#print axioms CoreObservedTrace.recordedInvariant25
#print axioms CoreObservedTrace.recordedInvariant26
#print axioms CoreObservedTrace.recordedInvariant27
#print axioms CoreObservedTrace.recordedInvariant28
#print axioms CoreObservedTrace.recordedInvariant29
#print axioms CoreObservedTrace.recordedInvariant3
#print axioms CoreObservedTrace.recordedInvariant30
#print axioms CoreObservedTrace.recordedInvariant31
#print axioms CoreObservedTrace.recordedInvariant32
#print axioms CoreObservedTrace.recordedInvariant33
#print axioms CoreObservedTrace.recordedInvariant34
#print axioms CoreObservedTrace.recordedInvariant35
#print axioms CoreObservedTrace.recordedInvariant36
#print axioms CoreObservedTrace.recordedInvariant37
#print axioms CoreObservedTrace.recordedInvariant38
#print axioms CoreObservedTrace.recordedInvariant39
#print axioms CoreObservedTrace.recordedInvariant4
#print axioms CoreObservedTrace.recordedInvariant40
#print axioms CoreObservedTrace.recordedInvariant41
#print axioms CoreObservedTrace.recordedInvariant42
#print axioms CoreObservedTrace.recordedInvariant43
#print axioms CoreObservedTrace.recordedInvariant44
#print axioms CoreObservedTrace.recordedInvariant45
#print axioms CoreObservedTrace.recordedInvariant46
#print axioms CoreObservedTrace.recordedInvariant47
#print axioms CoreObservedTrace.recordedInvariant48
#print axioms CoreObservedTrace.recordedInvariant49
#print axioms CoreObservedTrace.recordedInvariant5
#print axioms CoreObservedTrace.recordedInvariant50
#print axioms CoreObservedTrace.recordedInvariant51
#print axioms CoreObservedTrace.recordedInvariant52
#print axioms CoreObservedTrace.recordedInvariant53
#print axioms CoreObservedTrace.recordedInvariant54
#print axioms CoreObservedTrace.recordedInvariant55
#print axioms CoreObservedTrace.recordedInvariant56
#print axioms CoreObservedTrace.recordedInvariant57
#print axioms CoreObservedTrace.recordedInvariant58
#print axioms CoreObservedTrace.recordedInvariant59
#print axioms CoreObservedTrace.recordedInvariant6
#print axioms CoreObservedTrace.recordedInvariant60
#print axioms CoreObservedTrace.recordedInvariant61
#print axioms CoreObservedTrace.recordedInvariant62
#print axioms CoreObservedTrace.recordedInvariant63
#print axioms CoreObservedTrace.recordedInvariant64
#print axioms CoreObservedTrace.recordedInvariant7
#print axioms CoreObservedTrace.recordedInvariant8
#print axioms CoreObservedTrace.recordedInvariant9
#print axioms CoreObservedTrace.recordedPrefix0
#print axioms CoreObservedTrace.recordedPrefix1
#print axioms CoreObservedTrace.recordedPrefix10
#print axioms CoreObservedTrace.recordedPrefix11
#print axioms CoreObservedTrace.recordedPrefix12
#print axioms CoreObservedTrace.recordedPrefix13
#print axioms CoreObservedTrace.recordedPrefix14
#print axioms CoreObservedTrace.recordedPrefix15
#print axioms CoreObservedTrace.recordedPrefix16
#print axioms CoreObservedTrace.recordedPrefix17
#print axioms CoreObservedTrace.recordedPrefix18
#print axioms CoreObservedTrace.recordedPrefix19
#print axioms CoreObservedTrace.recordedPrefix2
#print axioms CoreObservedTrace.recordedPrefix20
#print axioms CoreObservedTrace.recordedPrefix21
#print axioms CoreObservedTrace.recordedPrefix22
#print axioms CoreObservedTrace.recordedPrefix23
#print axioms CoreObservedTrace.recordedPrefix24
#print axioms CoreObservedTrace.recordedPrefix25
#print axioms CoreObservedTrace.recordedPrefix26
#print axioms CoreObservedTrace.recordedPrefix27
#print axioms CoreObservedTrace.recordedPrefix28
#print axioms CoreObservedTrace.recordedPrefix29
#print axioms CoreObservedTrace.recordedPrefix3
#print axioms CoreObservedTrace.recordedPrefix30
#print axioms CoreObservedTrace.recordedPrefix31
#print axioms CoreObservedTrace.recordedPrefix32
#print axioms CoreObservedTrace.recordedPrefix33
#print axioms CoreObservedTrace.recordedPrefix34
#print axioms CoreObservedTrace.recordedPrefix35
#print axioms CoreObservedTrace.recordedPrefix36
#print axioms CoreObservedTrace.recordedPrefix37
#print axioms CoreObservedTrace.recordedPrefix38
#print axioms CoreObservedTrace.recordedPrefix39
#print axioms CoreObservedTrace.recordedPrefix4
#print axioms CoreObservedTrace.recordedPrefix40
#print axioms CoreObservedTrace.recordedPrefix41
#print axioms CoreObservedTrace.recordedPrefix42
#print axioms CoreObservedTrace.recordedPrefix43
#print axioms CoreObservedTrace.recordedPrefix44
#print axioms CoreObservedTrace.recordedPrefix45
#print axioms CoreObservedTrace.recordedPrefix46
#print axioms CoreObservedTrace.recordedPrefix47
#print axioms CoreObservedTrace.recordedPrefix48
#print axioms CoreObservedTrace.recordedPrefix49
#print axioms CoreObservedTrace.recordedPrefix5
#print axioms CoreObservedTrace.recordedPrefix50
#print axioms CoreObservedTrace.recordedPrefix51
#print axioms CoreObservedTrace.recordedPrefix52
#print axioms CoreObservedTrace.recordedPrefix53
#print axioms CoreObservedTrace.recordedPrefix54
#print axioms CoreObservedTrace.recordedPrefix55
#print axioms CoreObservedTrace.recordedPrefix56
#print axioms CoreObservedTrace.recordedPrefix57
#print axioms CoreObservedTrace.recordedPrefix58
#print axioms CoreObservedTrace.recordedPrefix59
#print axioms CoreObservedTrace.recordedPrefix6
#print axioms CoreObservedTrace.recordedPrefix60
#print axioms CoreObservedTrace.recordedPrefix61
#print axioms CoreObservedTrace.recordedPrefix62
#print axioms CoreObservedTrace.recordedPrefix63
#print axioms CoreObservedTrace.recordedPrefix64
#print axioms CoreObservedTrace.recordedPrefix7
#print axioms CoreObservedTrace.recordedPrefix8
#print axioms CoreObservedTrace.recordedPrefix9
#print axioms CoreObservedTrace.recordedSafe0
#print axioms CoreObservedTrace.recordedSafe1
#print axioms CoreObservedTrace.recordedSafe10
#print axioms CoreObservedTrace.recordedSafe11
#print axioms CoreObservedTrace.recordedSafe12
#print axioms CoreObservedTrace.recordedSafe13
#print axioms CoreObservedTrace.recordedSafe14
#print axioms CoreObservedTrace.recordedSafe15
#print axioms CoreObservedTrace.recordedSafe16
#print axioms CoreObservedTrace.recordedSafe17
#print axioms CoreObservedTrace.recordedSafe18
#print axioms CoreObservedTrace.recordedSafe19
#print axioms CoreObservedTrace.recordedSafe2
#print axioms CoreObservedTrace.recordedSafe20
#print axioms CoreObservedTrace.recordedSafe21
#print axioms CoreObservedTrace.recordedSafe22
#print axioms CoreObservedTrace.recordedSafe23
#print axioms CoreObservedTrace.recordedSafe24
#print axioms CoreObservedTrace.recordedSafe25
#print axioms CoreObservedTrace.recordedSafe26
#print axioms CoreObservedTrace.recordedSafe27
#print axioms CoreObservedTrace.recordedSafe28
#print axioms CoreObservedTrace.recordedSafe29
#print axioms CoreObservedTrace.recordedSafe3
#print axioms CoreObservedTrace.recordedSafe30
#print axioms CoreObservedTrace.recordedSafe31
#print axioms CoreObservedTrace.recordedSafe32
#print axioms CoreObservedTrace.recordedSafe33
#print axioms CoreObservedTrace.recordedSafe34
#print axioms CoreObservedTrace.recordedSafe35
#print axioms CoreObservedTrace.recordedSafe36
#print axioms CoreObservedTrace.recordedSafe37
#print axioms CoreObservedTrace.recordedSafe38
#print axioms CoreObservedTrace.recordedSafe39
#print axioms CoreObservedTrace.recordedSafe4
#print axioms CoreObservedTrace.recordedSafe40
#print axioms CoreObservedTrace.recordedSafe41
#print axioms CoreObservedTrace.recordedSafe42
#print axioms CoreObservedTrace.recordedSafe43
#print axioms CoreObservedTrace.recordedSafe44
#print axioms CoreObservedTrace.recordedSafe45
#print axioms CoreObservedTrace.recordedSafe46
#print axioms CoreObservedTrace.recordedSafe47
#print axioms CoreObservedTrace.recordedSafe48
#print axioms CoreObservedTrace.recordedSafe49
#print axioms CoreObservedTrace.recordedSafe5
#print axioms CoreObservedTrace.recordedSafe50
#print axioms CoreObservedTrace.recordedSafe51
#print axioms CoreObservedTrace.recordedSafe52
#print axioms CoreObservedTrace.recordedSafe53
#print axioms CoreObservedTrace.recordedSafe54
#print axioms CoreObservedTrace.recordedSafe55
#print axioms CoreObservedTrace.recordedSafe56
#print axioms CoreObservedTrace.recordedSafe57
#print axioms CoreObservedTrace.recordedSafe58
#print axioms CoreObservedTrace.recordedSafe59
#print axioms CoreObservedTrace.recordedSafe6
#print axioms CoreObservedTrace.recordedSafe60
#print axioms CoreObservedTrace.recordedSafe61
#print axioms CoreObservedTrace.recordedSafe62
#print axioms CoreObservedTrace.recordedSafe63
#print axioms CoreObservedTrace.recordedSafe64
#print axioms CoreObservedTrace.recordedSafe7
#print axioms CoreObservedTrace.recordedSafe8
#print axioms CoreObservedTrace.recordedSafe9
#print axioms CoreObservedTrace.recordedStep1
#print axioms CoreObservedTrace.recordedStep10
#print axioms CoreObservedTrace.recordedStep11
#print axioms CoreObservedTrace.recordedStep12
#print axioms CoreObservedTrace.recordedStep13
#print axioms CoreObservedTrace.recordedStep14
#print axioms CoreObservedTrace.recordedStep15
#print axioms CoreObservedTrace.recordedStep16
#print axioms CoreObservedTrace.recordedStep17
#print axioms CoreObservedTrace.recordedStep18
#print axioms CoreObservedTrace.recordedStep19
#print axioms CoreObservedTrace.recordedStep2
#print axioms CoreObservedTrace.recordedStep20
#print axioms CoreObservedTrace.recordedStep21
#print axioms CoreObservedTrace.recordedStep22
#print axioms CoreObservedTrace.recordedStep23
#print axioms CoreObservedTrace.recordedStep24
#print axioms CoreObservedTrace.recordedStep25
#print axioms CoreObservedTrace.recordedStep26
#print axioms CoreObservedTrace.recordedStep27
#print axioms CoreObservedTrace.recordedStep28
#print axioms CoreObservedTrace.recordedStep29
#print axioms CoreObservedTrace.recordedStep3
#print axioms CoreObservedTrace.recordedStep30
#print axioms CoreObservedTrace.recordedStep31
#print axioms CoreObservedTrace.recordedStep32
#print axioms CoreObservedTrace.recordedStep33
#print axioms CoreObservedTrace.recordedStep34
#print axioms CoreObservedTrace.recordedStep35
#print axioms CoreObservedTrace.recordedStep36
#print axioms CoreObservedTrace.recordedStep37
#print axioms CoreObservedTrace.recordedStep38
#print axioms CoreObservedTrace.recordedStep39
#print axioms CoreObservedTrace.recordedStep4
#print axioms CoreObservedTrace.recordedStep40
#print axioms CoreObservedTrace.recordedStep41
#print axioms CoreObservedTrace.recordedStep42
#print axioms CoreObservedTrace.recordedStep43
#print axioms CoreObservedTrace.recordedStep44
#print axioms CoreObservedTrace.recordedStep45
#print axioms CoreObservedTrace.recordedStep46
#print axioms CoreObservedTrace.recordedStep47
#print axioms CoreObservedTrace.recordedStep48
#print axioms CoreObservedTrace.recordedStep49
#print axioms CoreObservedTrace.recordedStep5
#print axioms CoreObservedTrace.recordedStep50
#print axioms CoreObservedTrace.recordedStep51
#print axioms CoreObservedTrace.recordedStep52
#print axioms CoreObservedTrace.recordedStep53
#print axioms CoreObservedTrace.recordedStep54
#print axioms CoreObservedTrace.recordedStep55
#print axioms CoreObservedTrace.recordedStep56
#print axioms CoreObservedTrace.recordedStep57
#print axioms CoreObservedTrace.recordedStep58
#print axioms CoreObservedTrace.recordedStep59
#print axioms CoreObservedTrace.recordedStep6
#print axioms CoreObservedTrace.recordedStep60
#print axioms CoreObservedTrace.recordedStep61
#print axioms CoreObservedTrace.recordedStep62
#print axioms CoreObservedTrace.recordedStep63
#print axioms CoreObservedTrace.recordedStep64
#print axioms CoreObservedTrace.recordedStep7
#print axioms CoreObservedTrace.recordedStep8
#print axioms CoreObservedTrace.recordedStep9
