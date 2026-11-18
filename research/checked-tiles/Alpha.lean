import Std

namespace CheckedAlpha

-- Straight coverage on two opaque byte channels in the same encoding.
def numerator (s d a : Nat) := a * s + (255 - a) * d

-- The author specifies the unique output with inequalities, independently
-- of the division instruction chosen by the compiler.
def law (s d a y : Nat) :=
  255 * y ≤ numerator s d a ∧ numerator s d a < 255 * (y + 1)

theorem floor_spec (s d a y : Nat) :
    law s d a y ↔ y = numerator s d a / 255 := by
  unfold law
  omega

theorem correlated_bound (s d a : Fin 256) :
    numerator s.val d.val a.val ≤ 65025 := by
  have h := Nat.add_le_add
    (Nat.mul_le_mul_left a.val (show s.val ≤ 255 by omega))
    (Nat.mul_le_mul_left (255 - a.val) (show d.val ≤ 255 by omega))
  rw [← Nat.add_mul, show a.val + (255 - a.val) = 255 by omega] at h
  exact h

-- A target can use two shifts by eight in unsigned lanes. Include the
-- intermediate bound because a correct Nat expression can overflow a lane.
theorem normalize (n : Nat) (h : n ≤ 65025) :
    (n + 1 + (n + 1) / 256) / 256 = n / 255 ∧
    n + 1 + (n + 1) / 256 < 65536 := by
  omega

theorem narrow_meets_law (s d a : Fin 256) :
    let n := numerator s.val d.val a.val
    law s.val d.val a.val ((n + 1 + (n + 1) / 256) / 256) := by
  exact (floor_spec ..).2 (normalize _ (correlated_bound s d a)).1

example : numerator 2 (numerator 2 0 127 / 255) 127 / 255 = 0 := by decide
-- Delaying the first division until the end yields a different output.
example : ((127 * 2 * 255) + 128 * numerator 2 0 127) / (255 * 255) = 1 := by decide

#print axioms narrow_meets_law
end CheckedAlpha
