import Std

/- A mathematical companion to the reviewed BL-to-SMT modulus expression.
   The definitions below describe integer mathematics, not execution of the BL
   compiler, the legacy SMT renderer, Z3, OxiZ or a BEAM instruction. In
   particular, successful value laws cannot establish exception preservation.
   The separate partial outcome explicitly refuses a zero divisor. -/
namespace FormalFloorModulus
set_option autoImplicit false

def repairedMod (a b : Int) : Int :=
  let e := a % b
  if e = 0 ∨ 0 < b then e else e + b

def repairedQuot (a b : Int) : Int :=
  if a % b = 0 ∨ 0 < b then a / b else a / b - 1

def outcome (a b : Int) : Option (Int × Int) :=
  if b = 0 then none else some (repairedQuot a b, repairedMod a b)

private theorem guard_equivalence (a b : Int) (hb : b ≠ 0) :
    (a % b = 0 ∨ 0 < b) ↔ (0 ≤ b ∨ b ∣ a) := by
  rw [Int.dvd_iff_emod_eq_zero]
  omega

theorem repaired_mod_eq_floor (a b : Int) (hb : b ≠ 0) :
    repairedMod a b = a.fmod b := by
  rw [Int.fmod_eq_emod]
  unfold repairedMod
  by_cases hg : a % b = 0 ∨ 0 < b
  · have hf := (guard_equivalence a b hb).mp hg
    simp [hg, hf]
  · have hf : ¬ (0 ≤ b ∨ b ∣ a) := fun h => hg ((guard_equivalence a b hb).mpr h)
    simp [hg, hf]

theorem repaired_quot_eq_floor (a b : Int) (hb : b ≠ 0) :
    repairedQuot a b = a.fdiv b := by
  rw [Int.fdiv_eq_ediv]
  unfold repairedQuot
  by_cases hg : a % b = 0 ∨ 0 < b
  · have hf := (guard_equivalence a b hb).mp hg
    simp [hg, hf]
  · have hf : ¬ (0 ≤ b ∨ b ∣ a) := fun h => hg ((guard_equivalence a b hb).mpr h)
    simp [hg, hf]

theorem reconstruction (a b : Int) (hb : b ≠ 0) :
    a = b * repairedQuot a b + repairedMod a b := by
  rw [repaired_quot_eq_floor a b hb, repaired_mod_eq_floor a b hb]
  exact (Int.mul_fdiv_add_fmod a b).symm

theorem positive_bounds (a b : Int) (hb : 0 < b) :
    0 ≤ repairedMod a b ∧ repairedMod a b < b := by
  have hn : b ≠ 0 := by omega
  simpa [repairedMod, hb] using
    And.intro (Int.emod_nonneg a hn) (Int.emod_lt_of_pos a hb)

private theorem negative_correction_bounds (e b : Int) (hb : b < 0)
    (lo : 0 ≤ e) (hi : e < -b) :
    b < (if e = 0 ∨ 0 < b then e else e + b) ∧
    (if e = 0 ∨ 0 < b then e else e + b) ≤ 0 := by
  have notPositive : ¬ 0 < b := Int.lt_asymm hb
  cases (inferInstance : Decidable (e = 0)) with
  | isTrue zero =>
    simp only [if_pos (Or.inl zero : e = 0 ∨ 0 < b)]
    constructor
    · simpa only [zero] using hb
    · simpa only [zero] using Int.le_refl 0
  | isFalse nonzero =>
    simp only [nonzero, false_or, notPositive, ite_false]
    have positive : 0 < e := Int.lt_iff_le_and_ne.mpr ⟨lo, Ne.symm nonzero⟩
    have upper : e + b < 0 := by
      simpa only [Int.neg_add_cancel] using Int.add_lt_add_right hi b
    exact ⟨Int.lt_add_of_pos_left b positive, Int.le_of_lt upper⟩

theorem negative_bounds (a b : Int) (hb : b < 0) :
    b < repairedMod a b ∧ repairedMod a b ≤ 0 := by
  have hn : b ≠ 0 := Int.ne_of_lt hb
  exact negative_correction_bounds (a % b) b hb
    (Int.emod_nonneg a hn) (Int.emod_lt_of_neg a hb)

theorem congruence (a b : Int) (hb : b ≠ 0) :
    b ∣ a - repairedMod a b := by
  rw [repaired_mod_eq_floor a b hb]
  exact Int.dvd_self_sub_fmod

theorem zero_is_failure (a : Int) : outcome a 0 = none := by
  simp [outcome]

theorem successful_outcome (a b : Int) (hb : b ≠ 0) :
    outcome a b = some (a.fdiv b, a.fmod b) := by
  simp [outcome, hb, repaired_quot_eq_floor a b hb, repaired_mod_eq_floor a b hb]

theorem defined_iff_nonzero (a b : Int) :
    (outcome a b).isSome = true ↔ b ≠ 0 := by
  by_cases hb : b = 0 <;> simp [outcome, hb]

theorem negative_divisor_counterexample :
    repairedMod 7 (-3) = -2 ∧ (7 : Int) % (-3) = 1 := by decide

#print axioms repaired_mod_eq_floor
#print axioms repaired_quot_eq_floor
#print axioms reconstruction
#print axioms positive_bounds
#print axioms negative_bounds
#print axioms congruence
#print axioms zero_is_failure
#print axioms successful_outcome
#print axioms defined_iff_nonzero
#print axioms negative_divisor_counterexample
end FormalFloorModulus
