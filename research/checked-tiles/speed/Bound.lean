import Std

namespace SerialRegion

def next (x : Nat) :=
  let t := 3*x + 1
  if t < 65521 then t else if t < 131042 then t - 65521 else t - 131042

theorem intermediates (x : Nat) (h : x < 65521) :
    3*x + 1 < 196563 ∧ next x < 65521 ∧ next x = (3*x+1) % 65521 := by
  unfold next
  split <;> try split <;> omega

def run : Nat → Nat → Nat
  | 0, x => x
  | n+1, x => run n (next x)

theorem invariant (n x : Nat) (h : x < 65521) : run n x < 65521 := by
  induction n generalizing x with
  | zero => exact h
  | succ n ih => exact ih _ (intermediates x h).2.1

#print axioms intermediates
#print axioms invariant
end SerialRegion
