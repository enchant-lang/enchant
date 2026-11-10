import CoreTerms

namespace CoreContract
open BeamLispCore FormalTerms FormalRefutation CoreTerms

/- A question proof and a Core proof can index the same named inputs differently.
   Rename the entire question, then transport its semantics along those maps. -/
def renameTerm (ints bools : Nat → Nat) : Term sort → Term sort
  | .int n => .int n
  | .bool b => .bool b
  | .inputInt index => .inputInt (ints index)
  | .inputBool index => .inputBool (bools index)
  | .add a b => .add (renameTerm ints bools a) (renameTerm ints bools b)
  | .sub a b => .sub (renameTerm ints bools a) (renameTerm ints bools b)
  | .mul a b => .mul (renameTerm ints bools a) (renameTerm ints bools b)
  | .neg a => .neg (renameTerm ints bools a)
  | .div a b => .div (renameTerm ints bools a) (renameTerm ints bools b)
  | .mod a b => .mod (renameTerm ints bools a) (renameTerm ints bools b)
  | .le a b => .le (renameTerm ints bools a) (renameTerm ints bools b)
  | .lt a b => .lt (renameTerm ints bools a) (renameTerm ints bools b)
  | .eqInt a b => .eqInt (renameTerm ints bools a) (renameTerm ints bools b)
  | .eqBool a b => .eqBool (renameTerm ints bools a) (renameTerm ints bools b)
  | .not a => .not (renameTerm ints bools a)
  | .and a b => .and (renameTerm ints bools a) (renameTerm ints bools b)
  | .or a b => .or (renameTerm ints bools a) (renameTerm ints bools b)
  | .implies a b => .implies (renameTerm ints bools a) (renameTerm ints bools b)
  | .xor a b => .xor (renameTerm ints bools a) (renameTerm ints bools b)
  | .ite c a b => .ite (renameTerm ints bools c) (renameTerm ints bools a) (renameTerm ints bools b)

theorem rename_eval (ints bools : Nat → Nat) (term : Term sort) (i : Nat → Int) (b : Nat → Bool) :
    (renameTerm ints bools term).eval i b = term.eval (fun n => i (ints n)) (fun n => b (bools n)) := by
  induction term <;> simp [renameTerm, Term.eval, *]

def renameQuestion (question : Question) (ints bools : Nat → Nat) : Question :=
  ⟨question.assertions.map (renameTerm ints bools), renameTerm ints bools question.claim⟩

theorem rename_entails (question : Question) (ints bools : Nat → Nat) (checked : question.entails) :
    (renameQuestion question ints bools).entails := by
  intro i b assumed
  change (renameTerm ints bools question.claim).eval i b = some true
  rw [rename_eval]
  apply checked
  intro assertion member
  rw [← rename_eval ints bools assertion i b]
  exact assumed _ (List.mem_map.mpr ⟨assertion, member, rfl⟩)

/- These folds match the term codec's variadic conjunction and disjunction.
   The outer true and the first true assertion come from q/prove on a raw term. -/
def both (a b : Term .boolean) : Term .boolean := .and a (.and b (.bool true))

def allowedTerm (error : Term .integer) : List Nat → Term .boolean
  | [] => .bool false
  | code :: more => .or (.eqInt error (.int (Int.ofNat code))) (allowedTerm error more)

def policyQuestion (pre post ok : Term .boolean) (error : Term .integer)
    (mustReturn : Bool) (allowed : List Nat) : Question :=
  let claim := if mustReturn then both ok post
               else both (.implies ok post) (.implies (.not ok) (allowedTerm error allowed))
  ⟨[.bool true, pre], both (.bool true) claim⟩

def holds (actual : Outcome τ) (value : Option (Value τ)) (post : Option Bool)
    (mustReturn : Bool) (allowed : List Nat) : Prop :=
  match actual with
  | .returned result => value = some result ∧ post = some true
  | .raised reason => mustReturn = false ∧ reason ∈ allowed.map errorName

@[simp] theorem and_known_true_left (x : Option Bool) : pAnd (some true) x = x := by
  cases x with
  | none => rfl
  | some flag => cases flag <;> rfl

@[simp] theorem and_known_true_right (x : Option Bool) : pAnd x (some true) = x := by
  cases x with
  | none => rfl
  | some flag => cases flag <;> rfl

@[simp] theorem or_known_false_left (x : Option Bool) : pOr (some false) x = x := by
  cases x with
  | none => rfl
  | some flag => cases flag <;> rfl

theorem allowed_eval (error : Term .integer) (allowed : List Nat) (i : Nat → Int) (b : Nat → Bool)
    (code : Int) (known : error.eval i b = some code) :
    (allowedTerm error allowed).eval i b = some (allowed.any fun n => decide (code = Int.ofNat n)) := by
  induction allowed with
  | nil => rfl
  | cons n more induction => simp [allowedTerm, Term.eval, known, strict₂, induction]

theorem named_allowed (catalogue allowed : List Nat) (reason : String)
    (positive : ∀ n ∈ allowed, 0 < n)
    (accepted : (allowed.any fun n => decide (errorCode catalogue reason = Int.ofNat n)) = true) :
    reason ∈ allowed.map errorName := by
  obtain ⟨code, member, acceptedCode⟩ := List.any_eq_true.mp accepted
  have codeEq : errorCode catalogue reason = Int.ofNat code := of_decide_eq_true acceptedCode
  have pos := positive code member
  unfold errorCode at codeEq
  cases found : catalogue.find? (fun n => errorName n == reason) with
  | none => simp [found] at codeEq; omega
  | some index =>
    have equal : index = code := Int.ofNat.inj (by simpa [found] using codeEq)
    have acceptedName : (errorName index == reason) = true := List.find?_some found
    have actual : errorName index = reason := beq_iff_eq.mp acceptedName
    exact List.mem_map.mpr ⟨code, member, equal ▸ actual⟩

theorem checked_claim_holds (pre post ok : Term .boolean) (error : Term .integer)
    (mustReturn : Bool) (allowed catalogue : List Nat) (positive : ∀ n ∈ allowed, 0 < n)
    (actual : Outcome τ) (value : Option (Value τ)) (i : Nat → Int) (b : Nat → Bool)
    (agreement : agrees actual (ok.eval i b) value (error.eval i b) (errorCode catalogue))
    (claim : (policyQuestion pre post ok error mustReturn allowed).claim.eval i b = some true) :
    holds actual value (post.eval i b) mustReturn allowed := by
  cases actual with
  | returned result =>
    obtain ⟨returned, payload, _⟩ := agrees_returned _ _ _ _ _ |>.mp agreement
    refine ⟨payload, ?_⟩
    cases mustReturn <;> simpa [policyQuestion, both, Term.eval, returned, pNot] using claim
  | raised reason =>
    obtain ⟨failed, errorKnown⟩ := agrees_raised _ _ _ _ _ |>.mp agreement
    cases mustReturn with
    | true => simp [policyQuestion, both, Term.eval, failed] at claim
    | false =>
      refine ⟨rfl, named_allowed catalogue allowed reason positive ?_⟩
      simpa [policyQuestion, both, Term.eval.eq_1, Term.eval.eq_2, Term.eval.eq_15,
        Term.eval.eq_16, Term.eval.eq_18, failed, pNot, allowed_eval error allowed i b _ errorKnown] using claim

theorem composed_contract (body : Expr context τ) (inputs : (Nat → Int) → (Nat → Bool) → Env context)
    (pre post ok : Term .boolean) (payload : Payload τ) (error : Term .integer)
    (mustReturn : Bool) (allowed catalogue : List Nat) (positive : ∀ n ∈ allowed, 0 < n)
    (agreement : ∀ i b, agrees (BeamLispCore.eval body (inputs i b))
      (ok.eval i b) (payload.eval i b) (error.eval i b) (errorCode catalogue))
    (entailment : (policyQuestion pre post ok error mustReturn allowed).entails) :
    ∀ i b, pre.eval i b = some true →
      holds (BeamLispCore.eval body (inputs i b)) (payload.eval i b) (post.eval i b) mustReturn allowed := by
  intro i b admitted
  apply checked_claim_holds pre post ok error mustReturn allowed catalogue positive _ _ i b (agreement i b)
  apply entailment
  intro assertion member
  simp only [policyQuestion, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with first | second
  · subst assertion; rfl
  · subst assertion; exact admitted

#print axioms rename_eval
#print axioms rename_entails
#print axioms allowed_eval
#print axioms named_allowed
#print axioms checked_claim_holds
#print axioms composed_contract
end CoreContract
