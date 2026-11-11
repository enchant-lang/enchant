import ActorTrace
import ActorPremises

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
set_option linter.unusedSimpArgs false
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop ActorTrace


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

def initialIntSlots : List Nat :=
[0]

def initialBoolSlots : List Nat :=
[]

def policy := StatePolicy.mk stateSlots stateIntCount stateBoolCount initialPredicate invariantPredicate
theorem invariantReadsStateOnly : replace policy.mask policy.inv = policy.inv := rfl

theorem stateSlotsCovered : policy.covered := by
  intro value left right
  apply inputs_ext
  · intro n
    cases n with
    | zero => rfl
    | succ n =>
      simp [StatePolicy.erase, policy, stateIntCount, stateBoolCount, Nat.succ_lt_succ_iff]
  · intro n
    simp [StatePolicy.erase, policy, stateIntCount, stateBoolCount, Nat.succ_lt_succ_iff]

theorem exactInitialQuestion :
    renameQuestion ActorInitTerms.originalQuestion (fun n => initialIntSlots[n]?.getD 0)
      (fun n => initialBoolSlots[n]?.getD 0) = policy.initQuestion := rfl

theorem initialStatesAreSafe : ∀ value, policy.initial value → policy.invariant value :=
  checked_init policy (exactInitialQuestion ▸ rename_entails ActorInitTerms.originalQuestion _ _
    ActorInitTerms.originalQuestionEntails)


def handlers : List (Handler (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)) := []

theorem allHandlersSafe : ∀ handler ∈ handlers, Safe handler policy.invariant := by
  intro handler member
  simp only [handlers, List.mem_cons, List.not_mem_nil, or_false] at member

theorem originalHandlerTracesSafe {events : List (Event handlers)} {final : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)}
    (trace : Trace handlers policy.initial events final) :
    policy.invariant final.1 ∧ final.2 = none :=
  trace_safe handlers policy.initial policy.invariant initialStatesAreSafe allHandlersSafe trace

theorem failureRetainsState {before : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)} {reason : String} {event : Event handlers}
    {after : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)}
    (transition : Step handlers (before, some reason) event after) :
    event = none ∧ after = (before, some reason) :=
  after_failure handlers transition

#print axioms stateSlotsCovered
#print axioms invariantReadsStateOnly
#print axioms exactInitialQuestion
#print axioms initialStatesAreSafe
#print axioms allHandlersSafe
#print axioms originalHandlerTracesSafe
#print axioms failureRetainsState
