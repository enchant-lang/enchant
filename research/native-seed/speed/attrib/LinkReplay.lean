/- A compiler operation with a deterministic continuation can consult a key
   chosen using earlier outcomes. `none` records a miss with the same weight
   as a hit. The model requires every relevant input or effect to be visible
   through a consultation or fixed outside the operation. -/
namespace NativeLinkReplay

inductive Computation (Key Value Result : Type) where
  | done (result : Result)
  | consult (key : Key) (next : Option Value → Computation Key Value Result)

def run (lookup : Key → Option Value) : Computation Key Value Result → Result
  | .done result => result
  | .consult key next => run lookup (next (lookup key))

def consulted (lookup : Key → Option Value) : Computation Key Value Result → List Key
  | .done _ => []
  | .consult key next => key :: consulted lookup (next (lookup key))

theorem replay (old new : Key → Option Value) (computation : Computation Key Value Result)
    (agree : ∀ key ∈ consulted old computation, new key = old key) :
    run new computation = run old computation ∧
      consulted new computation = consulted old computation := by
  induction computation with
  | done result => exact ⟨rfl, rfl⟩
  | consult key next ih =>
    have head : new key = old key := agree key (by simp [consulted])
    have tail : ∀ k ∈ consulted old (next (old key)), new k = old k := by
      intro k member
      exact agree k (by simp [consulted, member])
    obtain ⟨sameResult, sameKeys⟩ := ih (old key) tail
    exact ⟨by simpa only [run, head] using sameResult,
           by simp only [consulted, head, sameKeys]⟩

#print axioms replay

end NativeLinkReplay
