import Refutation

/- Mathematical Int/Bool terms, separate from BL program evaluation. Undefined
   integer division/modulus is explicit. Boolean dominance and selected arms
   can determine a result without interpreting an irrelevant undefined term. -/
namespace FormalTerms
open FormalRefutation

inductive Ty where
  | integer
  | boolean
  deriving DecidableEq, Repr

abbrev Ty.Value : Ty → Type
  | .integer => Int
  | .boolean => Bool

inductive Term : Ty → Type where
  | int : Int → Term .integer
  | bool : Bool → Term .boolean
  | inputInt : Nat → Term .integer
  | inputBool : Nat → Term .boolean
  | add : Term .integer → Term .integer → Term .integer
  | sub : Term .integer → Term .integer → Term .integer
  | mul : Term .integer → Term .integer → Term .integer
  | neg : Term .integer → Term .integer
  | div : Term .integer → Term .integer → Term .integer
  | mod : Term .integer → Term .integer → Term .integer
  | le : Term .integer → Term .integer → Term .boolean
  | lt : Term .integer → Term .integer → Term .boolean
  | eqInt : Term .integer → Term .integer → Term .boolean
  | eqBool : Term .boolean → Term .boolean → Term .boolean
  | not : Term .boolean → Term .boolean
  | and : Term .boolean → Term .boolean → Term .boolean
  | or : Term .boolean → Term .boolean → Term .boolean
  | implies : Term .boolean → Term .boolean → Term .boolean
  | xor : Term .boolean → Term .boolean → Term .boolean
  | ite {sort : Ty} : Term .boolean → Term sort → Term sort → Term sort

def strict₂ (operation : α → β → γ) (a : Option α) (b : Option β) : Option γ :=
  match a, b with
  | some x, some y => some (operation x y)
  | _, _ => none

def divide (a b : Int) : Option Int := if b = 0 then none else some (a / b)
def modulus (a b : Int) : Option Int := if b = 0 then none else some (a % b)
def partial₂ (operation : α → β → Option γ) (a : Option α) (b : Option β) : Option γ :=
  match a, b with
  | some x, some y => operation x y
  | _, _ => none

@[simp] theorem known_and (a b : Bool) : pAnd (some a) (some b) = some (a && b) := by cases a <;> cases b <;> rfl
@[simp] theorem known_or (a b : Bool) : pOr (some a) (some b) = some (a || b) := by cases a <;> cases b <;> rfl
@[simp] theorem known_not (a : Bool) : pNot (some a) = some (!a) := rfl
@[simp] theorem false_and (a : Option Bool) : pAnd (some false) a = some false := rfl
@[simp] theorem and_false (a : Option Bool) : pAnd a (some false) = some false := by cases a with
  | none => rfl
  | some a => cases a <;> rfl
@[simp] theorem true_or (a : Option Bool) : pOr (some true) a = some true := rfl
@[simp] theorem or_true (a : Option Bool) : pOr a (some true) = some true := by cases a with
  | none => rfl
  | some a => cases a <;> rfl

def Term.eval : {sort : Ty} → Term sort → (Nat → Int) → (Nat → Bool) → Option sort.Value
  | _, .int value, _, _ => some value
  | _, .bool value, _, _ => some value
  | _, .inputInt index, integers, _ => some (integers index)
  | _, .inputBool index, _, booleans => some (booleans index)
  | _, .add a b, i, p => strict₂ (· + ·) (a.eval i p) (b.eval i p)
  | _, .sub a b, i, p => strict₂ (· - ·) (a.eval i p) (b.eval i p)
  | _, .mul a b, i, p => strict₂ (· * ·) (a.eval i p) (b.eval i p)
  | _, .neg a, i, p => (a.eval i p).map (- ·)
  | _, .div a b, i, p => partial₂ divide (a.eval i p) (b.eval i p)
  | _, .mod a b, i, p => partial₂ modulus (a.eval i p) (b.eval i p)
  | _, .le a b, i, p => strict₂ (fun a b => decide (a ≤ b)) (a.eval i p) (b.eval i p)
  | _, .lt a b, i, p => strict₂ (fun a b => decide (a < b)) (a.eval i p) (b.eval i p)
  | _, .eqInt a b, i, p => strict₂ (fun a b => decide (a = b)) (a.eval i p) (b.eval i p)
  | _, .eqBool a b, i, p => strict₂ (fun a b => decide (a = b)) (a.eval i p) (b.eval i p)
  | _, .not a, i, p => pNot (a.eval i p)
  | _, .and a b, i, p => pAnd (a.eval i p) (b.eval i p)
  | _, .or a b, i, p => pOr (a.eval i p) (b.eval i p)
  | _, .implies a b, i, p => pOr (pNot (a.eval i p)) (b.eval i p)
  | _, .xor a b, i, p => strict₂ (fun a b => decide (a ≠ b)) (a.eval i p) (b.eval i p)
  | _, .ite condition yes no, i, p =>
    match condition.eval i p with
    | some true => yes.eval i p
    | some false => no.eval i p
    | none => none

structure Question where
  assertions : List (Term .boolean)
  claim : Term .boolean

def Question.assumed (question : Question) (integers : Nat → Int) (booleans : Nat → Bool) : Prop :=
  ∀ assertion ∈ question.assertions, assertion.eval integers booleans = some true
def Question.entails (question : Question) : Prop :=
  ∀ integers booleans, question.assumed integers booleans → question.claim.eval integers booleans = some true

/- This is the universal composition rule. Concrete generated proofs establish
   its countermodel-preservation premise for the exact original term trees. -/
theorem connected_refutation_entails (question : Question) (problem : Problem) (proof : Proof)
    (integerMap : (Nat → Int) → Nat → Int) (booleanMap : (Nat → Bool) → Nat → Bool)
    (connected : ∀ integers booleans, question.assumed integers booleans →
      question.claim.eval integers booleans ≠ some true →
      problem.satisfied (integerMap integers) (booleanMap booleans))
    (accepted : check problem proof = true) : question.entails := by
  intro integers booleans assumed
  by_cases good : question.claim.eval integers booleans = some true
  · exact good
  · exact False.elim (checked_refutation_unsatisfiable problem proof accepted
      (integerMap integers) (booleanMap booleans) (connected integers booleans assumed good))

theorem division_zero (a : Int) : divide a 0 = none := by simp [divide]
theorem modulus_zero (a : Int) : modulus a 0 = none := by simp [modulus]
theorem selected_true {sort : Ty} (yes no : Term sort) (integers booleans) :
    (Term.ite (.bool true) yes no).eval integers booleans = yes.eval integers booleans := rfl
theorem selected_false {sort : Ty} (yes no : Term sort) (integers booleans) :
    (Term.ite (.bool false) yes no).eval integers booleans = no.eval integers booleans := rfl
theorem false_dominates (value : Option Bool) : pAnd (some false) value = some false := rfl
theorem true_dominates (value : Option Bool) : pOr (some true) value = some true := rfl

#print axioms division_zero
#print axioms modulus_zero
#print axioms selected_true
#print axioms selected_false
#print axioms false_dominates
#print axioms true_dominates
#print axioms connected_refutation_entails
#print axioms known_and
#print axioms known_or
#print axioms known_not
#print axioms false_and
#print axioms and_false
#print axioms true_or
#print axioms or_true
end FormalTerms
