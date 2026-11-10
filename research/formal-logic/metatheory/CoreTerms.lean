import Core
import Terms

namespace CoreTerms
open BeamLispCore FormalTerms

/- A payload is the shaped value of a symbolic Core outcome. The Boolean
   success term and integer error term remain independent of this payload. -/
inductive Payload : BeamLispCore.Ty → Type where
  | integer : Term .integer → Payload .int
  | boolean : Term .boolean → Payload .bool
  | unit : Payload .unit
  | pair : Payload a → Payload b → Payload (.prod a b)

def Payload.eval : Payload τ → (Nat → Int) → (Nat → Bool) → Option (Value τ)
  | .integer value, i, b => value.eval i b
  | .boolean value, i, b => value.eval i b
  | .unit, _, _ => some ()
  | .pair left right, i, b => strict₂ Prod.mk (left.eval i b) (right.eval i b)

def agrees (actual : Outcome τ) (ok : Option Bool) (value : Option (Value τ))
    (error : Option Int) (code : String → Int) : Prop :=
  match actual with
  | .returned result => ok = some true ∧ value = some result ∧ error = some 0
  | .raised reason => ok = some false ∧ error = some (code reason)

def errorName (code : Nat) : String := if code = 1 then "zero-divisor" else "core-error/" ++ toString code

def errorCode (codes : List Nat) (reason : String) : Int :=
  Int.ofNat ((codes.find? fun code => errorName code == reason).getD 0)

/- These functions are the arithmetic formulas in formal.numeric. Core's
   reference operations are defined with tdiv/tmod in Core.lean. -/
def quotientValue (a b : Int) : Int :=
  a / b + if a < 0 ∧ 0 < a % b then (if 0 < b then 1 else -1) else 0

def remainderValue (a b : Int) : Int := a - b * quotientValue a b

def modulusValue (a b : Int) : Int :=
  let r := remainderValue a b
  if r = 0 ∨ decide (0 < a) = decide (0 < b) then r else r + b

theorem quotient_value (a b : Int) (nonzero : b ≠ 0) : quotientValue a b = a.tdiv b := by
  have nonnegative := Int.emod_nonneg a nonzero
  rw [Int.tdiv_eq_ediv, Int.dvd_iff_emod_eq_zero]
  by_cases negative : a < 0
  · have notNonneg : ¬ 0 ≤ a := by omega
    by_cases exactDivision : a % b = 0
    · simp [quotientValue, exactDivision]
    · have positiveRemainder : 0 < a % b := by omega
      by_cases positive : 0 < b
      · simp [quotientValue, negative, positiveRemainder, positive, notNonneg, exactDivision,
          Int.sign_eq_one_of_pos positive]
      · have negativeDivisor : b < 0 := by omega
        simp [quotientValue, negative, positiveRemainder, positive, notNonneg, exactDivision,
          Int.sign_eq_neg_one_of_neg negativeDivisor]
  · have nonneg : 0 ≤ a := by omega
    simp [quotientValue, negative, nonneg]

theorem remainder_value (a b : Int) (nonzero : b ≠ 0) : remainderValue a b = a.tmod b := by
  rw [remainderValue, quotient_value a b nonzero, Int.tmod_def]

theorem modulus_value (a b : Int) (nonzero : b ≠ 0) :
    modulusValue a b = (if a.tmod b ≠ 0 ∧ ((a.tmod b < 0 ∧ b > 0) ∨ (a.tmod b > 0 ∧ b < 0))
                         then a.tmod b + b else a.tmod b) := by
  unfold modulusValue
  rw [remainder_value a b nonzero]
  by_cases zero : a.tmod b = 0
  · simp [zero]
  · by_cases positiveA : 0 < a
    · have nonnegativeRemainder := Int.tmod_nonneg b (Int.le_of_lt positiveA)
      have positiveRemainder : 0 < a.tmod b := by omega
      have notNegativeRemainder : ¬ a.tmod b < 0 := by omega
      by_cases positiveB : 0 < b
      · have notNegativeB : ¬ b < 0 := by omega
        simp [zero, positiveA, positiveB, positiveRemainder, notNegativeRemainder, notNegativeB]
      · have negativeB : b < 0 := by omega
        simp [zero, positiveA, positiveB, positiveRemainder, notNegativeRemainder, negativeB]
    · have nonnegativeNeg : 0 ≤ -a := by omega
      have nonpositiveRemainder := Int.tmod_nonneg b nonnegativeNeg
      rw [Int.neg_tmod] at nonpositiveRemainder
      have negativeRemainder : a.tmod b < 0 := by omega
      have notPositiveRemainder : ¬ 0 < a.tmod b := by omega
      by_cases positiveB : 0 < b
      · simp [zero, positiveA, positiveB, negativeRemainder, notPositiveRemainder]
      · simp [zero, positiveA, positiveB, negativeRemainder, notPositiveRemainder]

theorem apply_quot (a b : Int) : IntOp.apply .quot a b =
    if b = 0 then .raised "zero-divisor" else .returned (quotientValue a b) := by
  by_cases zero : b = 0 <;> simp [IntOp.apply, zero, quotient_value]

theorem apply_rem (a b : Int) : IntOp.apply .rem a b =
    if b = 0 then .raised "zero-divisor" else .returned (remainderValue a b) := by
  by_cases zero : b = 0 <;> simp [IntOp.apply, zero, remainder_value]

theorem apply_mod (a b : Int) : IntOp.apply .mod a b =
    if b = 0 then .raised "zero-divisor" else .returned (modulusValue a b) := by
  by_cases zero : b = 0 <;> simp [IntOp.apply, zero, modulus_value]

#print axioms quotient_value
#print axioms remainder_value
#print axioms modulus_value
#print axioms apply_quot
#print axioms apply_rem
#print axioms apply_mod
end CoreTerms
