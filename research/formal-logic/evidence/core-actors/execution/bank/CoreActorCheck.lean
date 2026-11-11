import ActorTrace
import ActorPremises

set_option maxRecDepth 5000
set_option maxHeartbeats 8000000
set_option linter.unusedSimpArgs false
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract CoreLoop ActorTrace


def stateSlots :=
(Layout.pair (Layout.int 1) (Layout.pair (Layout.int 2) (Layout.pair (Layout.int 0) Layout.unit)))

def stateIntCount : Nat :=
3

def stateBoolCount : Nat :=
0

def initialPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.bool true) (Term.and (Term.and (Term.eqInt (Term.inputInt 1) (Term.int (Int.ofNat 0))) (Term.and (Term.eqInt (Term.inputInt 2) (Term.int (Int.ofNat 0))) (Term.and (Term.eqInt (Term.inputInt 0) (Term.int (Int.ofNat 0))) (Term.bool true)))) (Term.bool true)))

def invariantPredicate : Term FormalTerms.Ty.boolean :=
(Term.and (Term.and (Term.bool true) (Term.and (Term.eqInt (Term.inputInt 1) (Term.sub (Term.inputInt 2) (Term.inputInt 0))) (Term.bool true))) (Term.and (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 1)) (Term.bool true))) (Term.bool true)))

def initialIntSlots : List Nat :=
[0, 1, 2]

def initialBoolSlots : List Nat :=
[]

def admission0 : Term FormalTerms.Ty.boolean :=
(Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 3)) (Term.bool true)))) (Term.bool true)))) (Term.bool true))

def handler0IntSlots : List Nat :=
[0, 1, 2, 3]

def handler0BoolSlots : List Nat :=
[]

def admission1 : Term FormalTerms.Ty.boolean :=
(Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.and (Term.bool true) (Term.and (Term.bool true) (Term.and (Term.le (Term.int (Int.ofNat 0)) (Term.inputInt 3)) (Term.bool true)))) (Term.bool true)))) (Term.bool true))

def handler1IntSlots : List Nat :=
[0, 1, 2, 3]

def handler1BoolSlots : List Nat :=
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
      cases n with
      | zero => rfl
      | succ n =>
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


def handlerEnv0 (input : Inputs) := ActorHandlerCore0.originalInputs input.ints input.bools
def handler0 := coreHandler policy ActorHandlerCore0.originalProgram handlerEnv0 admission0

theorem handler0ReadsState (value : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)))) (message : Inputs) :
    (handlerEnv0 (stateSlots.put value message)).lookup (Var.succ Var.zero) = value := rfl

theorem exactHandler0Question :
    renameQuestion ActorHandlerTerms0.originalQuestion (fun i => handler0IntSlots[i]?.getD 0)
      (fun i => handler0BoolSlots[i]?.getD 0) =
      policy.handlerQuestion admission0 ActorHandlerCore0.symbolicOK ActorHandlerCore0.symbolicValue := rfl

theorem handler0Safe : Safe handler0 policy.invariant :=
  checked_handler policy stateSlotsCovered invariantReadsStateOnly
    ActorHandlerCore0.originalProgram handlerEnv0 admission0 ActorHandlerCore0.symbolicOK
    ActorHandlerCore0.symbolicValue ActorHandlerCore0.symbolicError (errorCode ActorHandlerCore0.errorCodes)
    (fun input => ActorHandlerCore0.coreTermCorrespondence input.ints input.bools)
    (exactHandler0Question ▸ rename_entails ActorHandlerTerms0.originalQuestion _ _
      ActorHandlerTerms0.originalQuestionEntails)


def handlerEnv1 (input : Inputs) := ActorHandlerCore1.originalInputs input.ints input.bools
def handler1 := coreHandler policy ActorHandlerCore1.originalProgram handlerEnv1 admission1

theorem handler1ReadsState (value : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)))) (message : Inputs) :
    (handlerEnv1 (stateSlots.put value message)).lookup (Var.succ Var.zero) = value := rfl

theorem exactHandler1Question :
    renameQuestion ActorHandlerTerms1.originalQuestion (fun i => handler1IntSlots[i]?.getD 0)
      (fun i => handler1BoolSlots[i]?.getD 0) =
      policy.handlerQuestion admission1 ActorHandlerCore1.symbolicOK ActorHandlerCore1.symbolicValue := rfl

theorem handler1Safe : Safe handler1 policy.invariant :=
  checked_handler policy stateSlotsCovered invariantReadsStateOnly
    ActorHandlerCore1.originalProgram handlerEnv1 admission1 ActorHandlerCore1.symbolicOK
    ActorHandlerCore1.symbolicValue ActorHandlerCore1.symbolicError (errorCode ActorHandlerCore1.errorCodes)
    (fun input => ActorHandlerCore1.coreTermCorrespondence input.ints input.bools)
    (exactHandler1Question ▸ rename_entails ActorHandlerTerms1.originalQuestion _ _
      ActorHandlerTerms1.originalQuestionEntails)


def handlers : List (Handler (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)))) := [handler0, handler1]

theorem allHandlersSafe : ∀ handler ∈ handlers, Safe handler policy.invariant := by
  intro handler member
  simp only [handlers, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with h0 | h1
  · subst handler; exact handler0Safe
  · subst handler; exact handler1Safe

theorem originalHandlerTracesSafe {events : List (Event handlers)} {final : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)))}
    (trace : Trace handlers policy.initial events final) :
    policy.invariant final.1 ∧ final.2 = none :=
  trace_safe handlers policy.initial policy.invariant initialStatesAreSafe allHandlersSafe trace

theorem failureRetainsState {before : Value (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)))} {reason : String} {event : Event handlers}
    {after : Configuration (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int (BeamLispCore.Ty.prod BeamLispCore.Ty.int BeamLispCore.Ty.unit)))}
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
#print axioms handler0ReadsState
#print axioms exactHandler0Question
#print axioms handler0Safe
#print axioms handler1ReadsState
#print axioms exactHandler1Question
#print axioms handler1Safe
