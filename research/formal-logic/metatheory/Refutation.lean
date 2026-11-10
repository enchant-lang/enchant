import Std

/- Executable normalized Boolean/linear refutation kernel. Its theorem applies
   to this actual checker. BL term normalization and the external data encoding
   are separate bridges; neither is assumed proved by the result below. -/
namespace FormalRefutation

def dot : List Int → (Nat → Int) → Int
  | [], _ => 0
  | c :: cs, env => c * env 0 + dot cs (fun i => env (i + 1))

def addCoefficients : List Int → List Int → List Int
  | [], ys => ys
  | xs, [] => xs
  | x :: xs, y :: ys => (x + y) :: addCoefficients xs ys

def scaleCoefficients (weight : Int) (cs : List Int) : List Int := cs.map (weight * ·)

theorem dot_add (xs ys : List Int) (env : Nat → Int) :
    dot (addCoefficients xs ys) env = dot xs env + dot ys env := by
  induction xs generalizing ys env with
  | nil => simp [addCoefficients, dot]
  | cons x xs ih =>
    cases ys with
    | nil => simp [addCoefficients, dot]
    | cons y ys =>
      simp only [addCoefficients, dot, ih, Int.add_mul]
      omega

theorem dot_scale (weight : Int) (xs : List Int) (env : Nat → Int) :
    dot (scaleCoefficients weight xs) env = weight * dot xs env := by
  induction xs generalizing env with
  | nil => simp [scaleCoefficients, dot]
  | cons x xs ih =>
    change weight * x * env 0 + dot (scaleCoefficients weight xs) (fun i => env (i + 1)) = _
    rw [ih]
    simp [dot, Int.mul_add, Int.mul_assoc]

structure Row where
  coefficients : List Int
  bound : Int
  deriving Repr, DecidableEq

def Row.holds (row : Row) (env : Nat → Int) : Prop := dot row.coefficients env ≤ row.bound
instance (row : Row) (env : Nat → Int) : Decidable (row.holds env) :=
  inferInstanceAs (Decidable (dot row.coefficients env ≤ row.bound))
def Row.zero : Row := ⟨[], 0⟩
def Row.add (a b : Row) : Row := ⟨addCoefficients a.coefficients b.coefficients, a.bound + b.bound⟩
def Row.scale (weight : Nat) (row : Row) : Row :=
  ⟨scaleCoefficients (Int.ofNat weight) row.coefficients, Int.ofNat weight * row.bound⟩
def Row.complement (row : Row) : Row := ⟨scaleCoefficients (-1) row.coefficients, -row.bound - 1⟩

theorem zero_holds (env : Nat → Int) : Row.zero.holds env := by simp [Row.zero, Row.holds, dot]
theorem add_holds (a b : Row) (env : Nat → Int) (ha : a.holds env) (hb : b.holds env) :
    (a.add b).holds env := by
  simp only [Row.holds, Row.add, dot_add] at *
  omega
theorem scale_holds (weight : Nat) (row : Row) (env : Nat → Int) (h : row.holds env) :
    (row.scale weight).holds env := by
  simp only [Row.holds, Row.scale, dot_scale] at *
  exact Int.mul_le_mul_of_nonneg_left h (Int.natCast_nonneg weight)
theorem complement_holds (row : Row) (env : Nat → Int) (h : ¬ row.holds env) :
    row.complement.holds env := by
  simp only [Row.holds, Row.complement, dot_scale] at *
  omega

def zeroCoefficients (cs : List Int) : Bool := cs.all (fun c => decide (c = 0))
theorem dot_zero (cs : List Int) (env : Nat → Int) (h : zeroCoefficients cs = true) : dot cs env = 0 := by
  induction cs generalizing env with
  | nil => rfl
  | cons c cs ih =>
    simp only [zeroCoefficients, List.all_cons, Bool.and_eq_true, decide_eq_true_eq] at h
    simp [dot, h.1, ih _ h.2]
theorem contradictory_row (row : Row) (env : Nat → Int)
    (zero : zeroCoefficients row.coefficients = true) (negative : row.bound < 0) : ¬ row.holds env := by
  simp only [Row.holds, dot_zero _ _ zero]
  omega

inductive Formula where
  | constant : Bool → Formula
  | atom : Nat → Formula
  | neg : Formula → Formula
  | both : Formula → Formula → Formula
  | either : Formula → Formula → Formula
  deriving Repr, DecidableEq

def Formula.eval : Formula → (Nat → Bool) → Bool
  | .constant value, _ => value
  | .atom id, values => values id
  | .neg f, values => !(f.eval values)
  | .both a b, values => a.eval values && b.eval values
  | .either a b, values => a.eval values || b.eval values

def pNot : Option Bool → Option Bool
  | none => none
  | some value => some (!value)
def pAnd : Option Bool → Option Bool → Option Bool
  | some false, _ => some false
  | _, some false => some false
  | some true, some true => some true
  | _, _ => none
def pOr : Option Bool → Option Bool → Option Bool
  | some true, _ => some true
  | _, some true => some true
  | some false, some false => some false
  | _, _ => none

def SoundOption (observed : Option Bool) (value : Bool) : Prop :=
  ∀ b, observed = some b → value = b

theorem not_sound (observed : Option Bool) (value : Bool) (h : SoundOption observed value) :
    SoundOption (pNot observed) (!value) := by
  cases observed <;> cases value <;> simp_all [SoundOption, pNot]
theorem and_sound (a b : Option Bool) (x y : Bool) (ha : SoundOption a x) (hb : SoundOption b y) :
    SoundOption (pAnd a b) (x && y) := by
  cases a <;> cases b <;> cases x <;> cases y <;> simp_all [SoundOption, pAnd]
theorem or_sound (a b : Option Bool) (x y : Bool) (ha : SoundOption a x) (hb : SoundOption b y) :
    SoundOption (pOr a b) (x || y) := by
  cases a <;> cases b <;> cases x <;> cases y <;> simp_all [SoundOption, pOr]

abbrev Assignment := Nat → Option Bool
def Consistent (assignment : Assignment) (values : Nat → Bool) : Prop :=
  ∀ id, SoundOption (assignment id) (values id)

def Formula.partial : Formula → Assignment → Option Bool
  | .constant value, _ => some value
  | .atom id, assignment => assignment id
  | .neg f, assignment => pNot (f.partial assignment)
  | .both a b, assignment => pAnd (a.partial assignment) (b.partial assignment)
  | .either a b, assignment => pOr (a.partial assignment) (b.partial assignment)

theorem partial_sound (f : Formula) (assignment : Assignment) (values : Nat → Bool)
    (h : Consistent assignment values) : SoundOption (f.partial assignment) (f.eval values) := by
  induction f with
  | constant value => simp [Formula.partial, Formula.eval, SoundOption]
  | atom id => exact h id
  | neg f ih => exact not_sound _ _ ih
  | both a b ha hb => exact and_sound _ _ _ _ ha hb
  | either a b ha hb => exact or_sound _ _ _ _ ha hb

def write (assignment : Assignment) (id : Nat) (value : Bool) : Assignment :=
  fun index => if index = id then some value else assignment index
theorem consistent_write (assignment : Assignment) (values : Nat → Bool) (id : Nat) (value : Bool)
    (h : Consistent assignment values) (hv : values id = value) : Consistent (write assignment id value) values := by
  intro index
  by_cases same : index = id
  · subst index; simp [write, SoundOption, hv]
  · simpa [write, same] using h index

inductive Atom where
  | boolean
  | linear : Row → Atom
  deriving Repr, DecidableEq

structure Problem where
  atoms : List Atom
  formulas : List Formula
  deriving Repr, DecidableEq

def Problem.values (problem : Problem) (integers : Nat → Int) (booleans : Nat → Bool) (id : Nat) : Bool :=
  match problem.atoms[id]? with
  | some .boolean => booleans id
  | some (.linear row) => decide (row.holds integers)
  | none => false
def Problem.satisfied (problem : Problem) (integers : Nat → Int) (booleans : Nat → Bool) : Prop :=
  ∀ f ∈ problem.formulas, f.eval (problem.values integers booleans) = true

def selectedRow (problem : Problem) (assignment : Assignment) (id : Nat) : Option Row :=
  match problem.atoms[id]?, assignment id with
  | some (.linear row), some true => some row
  | some (.linear row), some false => some row.complement
  | _, _ => none

theorem selected_row_sound (problem : Problem) (assignment : Assignment) (integers : Nat → Int)
    (booleans : Nat → Bool) (h : Consistent assignment (problem.values integers booleans))
    (id : Nat) (row : Row) (selected : selectedRow problem assignment id = some row) : row.holds integers := by
  cases lookup : problem.atoms[id]? with
  | none => simp [selectedRow, lookup] at selected
  | some atom =>
    cases atom with
    | boolean => simp [selectedRow, lookup] at selected
    | linear original =>
      cases assigned : assignment id with
      | none => simp [selectedRow, lookup, assigned] at selected
      | some value =>
        have hv := h id value assigned
        simp only [Problem.values, lookup] at hv
        cases value with
        | false =>
          simp only [selectedRow, lookup, assigned, Option.some.injEq] at selected
          subst row
          exact complement_holds original integers (of_decide_eq_false hv)
        | true =>
          simp only [selectedRow, lookup, assigned, Option.some.injEq] at selected
          subst row
          exact of_decide_eq_true hv

def sumRows (problem : Problem) (assignment : Assignment) : List (Nat × Nat) → Option Row
  | [] => some Row.zero
  | (id, weight) :: rest =>
    if weight = 0 then none
    else match selectedRow problem assignment id, sumRows problem assignment rest with
      | some row, some total => some ((row.scale weight).add total)
      | _, _ => none

theorem sum_rows_sound (problem : Problem) (assignment : Assignment) (integers : Nat → Int)
    (booleans : Nat → Bool) (consistent : Consistent assignment (problem.values integers booleans))
    (weights : List (Nat × Nat)) (total : Row) (summed : sumRows problem assignment weights = some total) :
    total.holds integers := by
  induction weights generalizing total with
  | nil => simp only [sumRows, Option.some.injEq] at summed; subst total; exact zero_holds integers
  | cons entry rest ih =>
    rcases entry with ⟨id, weight⟩
    simp only [sumRows] at summed
    split at summed
    · contradiction
    · cases chosen : selectedRow problem assignment id with
      | none => simp [chosen] at summed
      | some row =>
        cases remaining : sumRows problem assignment rest with
        | none => simp [chosen, remaining] at summed
        | some tail =>
          simp only [chosen, remaining, Option.some.injEq] at summed
          subst total
          exact add_holds _ _ integers
            (scale_holds weight row integers (selected_row_sound problem assignment integers booleans consistent id row chosen))
            (ih tail remaining)

inductive Proof where
  | boolean
  | linear : List (Nat × Nat) → Proof
  | split : Nat → Proof → Proof → Proof
  deriving Repr, DecidableEq

def checkFrom (problem : Problem) : Proof → Assignment → Bool
  | .boolean, assignment => problem.formulas.any (fun f => decide (f.partial assignment = some false))
  | .linear weights, assignment =>
    match weights, sumRows problem assignment weights with
    | [], _ => false
    | _, some total => zeroCoefficients total.coefficients && decide (total.bound < 0)
    | _, none => false
  | .split id yes no, assignment =>
    if id < problem.atoms.length ∧ assignment id = none then
      checkFrom problem yes (write assignment id true) && checkFrom problem no (write assignment id false)
    else false

theorem check_from_sound (problem : Problem) (proof : Proof) (integers : Nat → Int) (booleans : Nat → Bool) :
    ∀ assignment, Consistent assignment (problem.values integers booleans) →
      problem.satisfied integers booleans → checkFrom problem proof assignment = true → False := by
  induction proof with
  | boolean =>
    intro assignment consistent satisfied accepted
    obtain ⟨formula, member, failed⟩ := List.any_eq_true.mp accepted
    have falseValue := partial_sound formula assignment _ consistent false (of_decide_eq_true failed)
    have trueValue := satisfied formula member
    simp_all
  | linear weights =>
    intro assignment consistent satisfied accepted
    cases weights with
    | nil => simp [checkFrom] at accepted
    | cons entry rest =>
      cases summed : sumRows problem assignment (entry :: rest) with
      | none => simp [checkFrom, summed] at accepted
      | some total =>
        have parts : zeroCoefficients total.coefficients = true ∧ total.bound < 0 := by
          simpa [checkFrom, summed] using accepted
        exact contradictory_row total integers parts.1 parts.2
          (sum_rows_sound problem assignment integers booleans consistent _ total summed)
  | split id yes no hy hn =>
    intro assignment consistent satisfied accepted
    simp only [checkFrom] at accepted
    split at accepted
    · have parts : checkFrom problem yes (write assignment id true) = true ∧
          checkFrom problem no (write assignment id false) = true := by simpa using accepted
      cases value : problem.values integers booleans id with
      | false => exact hn _ (consistent_write assignment _ id false consistent value) satisfied parts.2
      | true => exact hy _ (consistent_write assignment _ id true consistent value) satisfied parts.1
    · contradiction

def check (problem : Problem) (proof : Proof) : Bool := checkFrom problem proof (fun _ => none)

theorem checked_refutation_unsatisfiable (problem : Problem) (proof : Proof) (accepted : check problem proof = true) :
    ∀ integers booleans, ¬ problem.satisfied integers booleans := by
  intro integers booleans satisfied
  exact check_from_sound problem proof integers booleans (fun _ => none)
    (by intro id value impossible; contradiction) satisfied accepted

#print axioms dot_add
#print axioms dot_scale
#print axioms zero_holds
#print axioms add_holds
#print axioms scale_holds
#print axioms complement_holds
#print axioms dot_zero
#print axioms contradictory_row
#print axioms not_sound
#print axioms and_sound
#print axioms or_sound
#print axioms partial_sound
#print axioms consistent_write
#print axioms selected_row_sound
#print axioms sum_rows_sound
#print axioms check_from_sound
#print axioms checked_refutation_unsatisfiable

end FormalRefutation
