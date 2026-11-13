import Terms
import FloorModulus

/- Connection inside the typed mathematical term model. This is not a theorem
   about the BL map/graph decoder, term constructors, legacy renderer, compiler,
   native solver implementation or concrete exception class. -/
namespace FormalTermFloorModulus
open FormalTerms FormalRefutation FormalFloorModulus
set_option autoImplicit false

def floorModTerm (a b : Term .integer) : Term .integer :=
  let e := Term.mod a b
  .ite (.or (.eqInt e (.int 0)) (.lt (.int 0) b)) e (.add e b)

theorem known_value (a b : Term .integer) (integers : Nat → Int) (booleans : Nat → Bool)
    (av bv : Int) (ha : a.eval integers booleans = some av)
    (hb : b.eval integers booleans = some bv) (nonzero : bv ≠ 0) :
    (floorModTerm a b).eval integers booleans = some (repairedMod av bv) := by
  cases (inferInstance : Decidable (av % bv = 0)) with
  | isTrue zero =>
    simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, modulus, nonzero,
          pOr, repairedMod, zero]
  | isFalse nonzeroRemainder =>
    cases (inferInstance : Decidable (0 < bv)) with
    | isTrue positive =>
      simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, modulus, nonzero,
            pOr, repairedMod, nonzeroRemainder, positive]
    | isFalse notPositive =>
      simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, modulus, nonzero,
            pOr, repairedMod, nonzeroRemainder, notPositive]

theorem known_floor_value (a b : Term .integer) (integers : Nat → Int) (booleans : Nat → Bool)
    (av bv : Int) (ha : a.eval integers booleans = some av)
    (hb : b.eval integers booleans = some bv) (nonzero : bv ≠ 0) :
    (floorModTerm a b).eval integers booleans = some (av.fmod bv) := by
  rw [known_value a b integers booleans av bv ha hb nonzero,
      repaired_mod_eq_floor av bv nonzero]

theorem zero_failure (a b : Term .integer) (integers : Nat → Int) (booleans : Nat → Bool)
    (hb : b.eval integers booleans = some 0) :
    (floorModTerm a b).eval integers booleans = none := by
  cases ha : a.eval integers booleans <;>
    simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, modulus, pOr]

theorem missing_left (a b : Term .integer) (integers : Nat → Int) (booleans : Nat → Bool)
    (ha : a.eval integers booleans = none) :
    (floorModTerm a b).eval integers booleans = none := by
  cases hb : b.eval integers booleans with
  | none => simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, pOr]
  | some bv =>
    cases (inferInstance : Decidable (0 < bv)) with
    | isTrue positive =>
      simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, pOr, positive]
    | isFalse notPositive =>
      simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, pOr, notPositive]

theorem missing_right (a b : Term .integer) (integers : Nat → Int) (booleans : Nat → Bool)
    (hb : b.eval integers booleans = none) :
    (floorModTerm a b).eval integers booleans = none := by
  cases ha : a.eval integers booleans <;>
    simp [floorModTerm, Term.eval, ha, hb, strict₂, partial₂, pOr]

theorem negative_divisor_example (integers : Nat → Int) (booleans : Nat → Bool) :
    (floorModTerm (.int 7) (.int (-3))).eval integers booleans = some (-2) ∧
    (Term.mod (.int 7) (.int (-3))).eval integers booleans = some 1 := by
  constructor <;> rfl

#print axioms known_value
#print axioms known_floor_value
#print axioms zero_failure
#print axioms missing_left
#print axioms missing_right
#print axioms negative_divisor_example
end FormalTermFloorModulus
