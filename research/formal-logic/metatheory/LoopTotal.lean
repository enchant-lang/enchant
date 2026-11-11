import Core

namespace LoopTotal
open BeamLispCore

/- This relation describes an actual finite chain of controller evaluations.
   The exit state is observable in the postcondition. -/
inductive Returns (step : State → Except String (LoopStep State Result)) :
    State → State → Result → Prop where
  | exit : step state = .ok (.finished result) → Returns step state state result
  | recur : step state = .ok (.again next) → Returns step next last result →
      Returns step state last result

def decreases (next current : Int × Int) : Prop :=
  next.1 < current.1 ∨ (next.1 = current.1 ∧ next.2 < current.2)

def admissibleStep (step : State → Except String (LoopStep State Result))
    (good : State → Prop) (rank : State → Int × Int) (post : State → Result → Prop)
    (state : State) : Prop :=
  match step state with
  | .error _ => False
  | .ok (.finished result) => post state result
  | .ok (.again next) => good next ∧ decreases (rank next) (rank state)

/- Run the controller on the invariant subtype. The failure case is eliminated
   by the checked step premise, and the next state carries invariant evidence. -/
def restrictedStep (step : State → Except String (LoopStep State Result))
    (good : State → Prop) (rank : State → Int × Int) (post : State → Result → Prop)
    (safe : ∀ state, good state → admissibleStep step good rank post state)
    (state : Subtype good) : LoopStep (Subtype good) (State × Result) :=
  match h : step state.val with
  | .error _ => False.elim (by simpa only [admissibleStep, h] using safe state.val state.property)
  | .ok (.finished result) => .finished (state.val, result)
  | .ok (.again next) => .again ⟨next, (show good next ∧ decreases (rank next) (rank state.val) by
      simpa only [admissibleStep, h] using safe state.val state.property).1⟩

theorem restricted_wellFounded (step : State → Except String (LoopStep State Result))
    (good : State → Prop) (rank : State → Int × Int) (post : State → Result → Prop)
    (safe : ∀ state, good state → admissibleStep step good rank post state)
    (nonnegative : ∀ state, good state → 0 ≤ (rank state).1 ∧ 0 ≤ (rank state).2) :
    WellFounded (fun next current => restrictedStep step good rank post safe current = .again next) := by
  apply integer_pair_rank_wellFounded (fun state : Subtype good => rank state.val)
    (fun current next => restrictedStep step good rank post safe current = .again next)
    (fun state => nonnegative state.val state.property)
  intro current next edge
  unfold restrictedStep at edge
  split at edge
  · rename_i failure failed
    exact False.elim (by simpa only [admissibleStep, failed] using safe current.val current.property)
  · cases edge
  · rename_i target taken
    cases edge
    exact (show good target ∧ decreases (rank target) (rank current.val) by
      simpa only [admissibleStep, taken] using safe current.val current.property).2

theorem run_restricted (step : State → Except String (LoopStep State Result))
    (good : State → Prop) (rank : State → Int × Int) (post : State → Result → Prop)
    (safe : ∀ state, good state → admissibleStep step good rank post state)
    (wf : WellFounded (fun next current => restrictedStep step good rank post safe current = .again next)) :
    ∀ state : Subtype good,
      let result := runLoop (restrictedStep step good rank post safe) wf state
      Returns step state.val result.1 result.2 ∧ good result.1 ∧ post result.1 result.2 := by
  intro state
  induction state using wf.induction with
  | h state ih =>
    dsimp only
    rw [runLoop_equation]
    cases actual : step state.val with
    | error reason =>
      exact False.elim (by simpa only [admissibleStep, actual] using safe state.val state.property)
    | ok action =>
      cases action with
      | finished value =>
        have chosen : restrictedStep step good rank post safe state = .finished (state.val, value) := by
          unfold restrictedStep; split <;> simp_all
        rw [chosen]
        exact ⟨.exit actual, state.property, by simpa only [admissibleStep, actual] using safe state.val state.property⟩
      | again next =>
        have nextGood : good next := (show good next ∧ decreases (rank next) (rank state.val) by
          simpa only [admissibleStep, actual] using safe state.val state.property).1
        let successor : Subtype good := ⟨next, nextGood⟩
        have chosen : restrictedStep step good rank post safe state = .again successor := by
          unfold restrictedStep; split <;> simp_all [successor]
        rw [chosen]
        obtain ⟨path, exitGood, exitPost⟩ := ih successor chosen
        exact ⟨.recur actual path, exitGood, exitPost⟩

theorem terminates (step : State → Except String (LoopStep State Result))
    (good : State → Prop) (rank : State → Int × Int) (post : State → Result → Prop)
    (safe : ∀ state, good state → admissibleStep step good rank post state)
    (nonnegative : ∀ state, good state → 0 ≤ (rank state).1 ∧ 0 ≤ (rank state).2)
    (initial : State) (initialGood : good initial) :
    ∃ last result, Returns step initial last result ∧ good last ∧ post last result := by
  let wf := restricted_wellFounded step good rank post safe nonnegative
  let state : Subtype good := ⟨initial, initialGood⟩
  let result := runLoop (restrictedStep step good rank post safe) wf state
  exact ⟨result.1, result.2, run_restricted step good rank post safe wf state⟩

#print axioms restricted_wellFounded
#print axioms run_restricted
#print axioms terminates
end LoopTotal
