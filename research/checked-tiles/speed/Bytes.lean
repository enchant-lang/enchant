import Std

namespace ByteFold

def bit (inside : Bool) : Nat := if inside then 1 else 0

def update (state byte : Nat) :=
  let base := 2 * (state / 2)
  let digit := if byte < 48 then 0 else if byte < 58 then 1 else 0
  if digit < 1 then base else if state < base + 1 then base + 3 else state

theorem scan_step (runs byte : Nat) (inside : Bool) :
    update (2*runs + bit inside) byte =
    2*(runs + (if 48 ≤ byte ∧ byte < 58 ∧ inside = false then 1 else 0))
    + (if 48 ≤ byte ∧ byte < 58 then 1 else 0) := by
  cases inside <;> by_cases lo : byte < 48 <;> by_cases hi : byte < 58 <;>
    by_cases above : 48 ≤ byte <;> simp [update, bit, lo, hi, above] <;> (repeat' split) <;> omega

theorem byte_grade (b : Nat) (h : b < 256) : (b + 255) / 2 ≤ 255 := by omega
#print axioms scan_step
#print axioms byte_grade
end ByteFold
