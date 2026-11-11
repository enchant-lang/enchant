import CoreContract
import LoopTotal

namespace CoreLoop
open BeamLispCore FormalTerms FormalRefutation CoreTerms CoreContract LoopTotal

structure Inputs where
  ints : Nat → Int
  bools : Nat → Bool

structure Replacement where
  ints : Nat → Term .integer
  bools : Nat → Term .boolean

def Replacement.identity : Replacement := ⟨Term.inputInt, Term.inputBool⟩

def replace (r : Replacement) : Term sort → Term sort
  | .int n => .int n
  | .bool b => .bool b
  | .inputInt index => r.ints index
  | .inputBool index => r.bools index
  | .add a b => .add (replace r a) (replace r b)
  | .sub a b => .sub (replace r a) (replace r b)
  | .mul a b => .mul (replace r a) (replace r b)
  | .neg a => .neg (replace r a)
  | .div a b => .div (replace r a) (replace r b)
  | .mod a b => .mod (replace r a) (replace r b)
  | .le a b => .le (replace r a) (replace r b)
  | .lt a b => .lt (replace r a) (replace r b)
  | .eqInt a b => .eqInt (replace r a) (replace r b)
  | .eqBool a b => .eqBool (replace r a) (replace r b)
  | .not a => .not (replace r a)
  | .and a b => .and (replace r a) (replace r b)
  | .or a b => .or (replace r a) (replace r b)
  | .implies a b => .implies (replace r a) (replace r b)
  | .xor a b => .xor (replace r a) (replace r b)
  | .ite c a b => .ite (replace r c) (replace r a) (replace r b)

def reads (r : Replacement) (current next : Inputs) : Prop :=
  (∀ n, (r.ints n).eval current.ints current.bools = some (next.ints n)) ∧
  (∀ n, (r.bools n).eval current.ints current.bools = some (next.bools n))

theorem replacement_eval (r : Replacement) (current next : Inputs) (matchInputs : reads r current next)
    (term : Term sort) : (replace r term).eval current.ints current.bools = term.eval next.ints next.bools := by
  induction term <;> simp [replace, Term.eval, matchInputs.1, matchInputs.2, *]

inductive Layout : BeamLispCore.Ty → Type where
  | int : Nat → Layout .int
  | bool : Nat → Layout .bool
  | unit : Layout .unit
  | pair : Layout a → Layout b → Layout (.prod a b)

def Layout.put : Layout τ → Value τ → Inputs → Inputs
  | .int slot, value, input => {input with ints := fun n => if n = slot then value else input.ints n}
  | .bool slot, value, input => {input with bools := fun n => if n = slot then value else input.bools n}
  | .unit, _, input => input
  | .pair left right, value, input => right.put value.2 (left.put value.1 input)

def Layout.plug : Layout τ → Payload τ → Replacement → Replacement
  | .int slot, .integer value, r => {r with ints := fun n => if n = slot then value else r.ints n}
  | .bool slot, .boolean value, r => {r with bools := fun n => if n = slot then value else r.bools n}
  | .unit, .unit, r => r
  | .pair left right, .pair a b, r => right.plug b (left.plug a r)

theorem Layout.plug_reads (slots : Layout τ) (payload : Payload τ) (value : Value τ)
    (current next : Inputs) (r : Replacement) (matchInputs : reads r current next)
    (known : payload.eval current.ints current.bools = some value) :
    reads (slots.plug payload r) current (slots.put value next) := by
  induction slots generalizing r next with
  | int slot =>
    cases payload with
    | integer term =>
      refine ⟨fun n => ?_, matchInputs.2⟩
      by_cases same : n = slot <;> simp [Layout.plug, Layout.put, same, matchInputs.1, Payload.eval] at known ⊢
  | bool slot =>
    cases payload with
    | boolean term =>
      refine ⟨matchInputs.1, fun n => ?_⟩
      by_cases same : n = slot <;> simp [Layout.plug, Layout.put, same, matchInputs.2, Payload.eval] at known ⊢
  | unit => cases payload; exact matchInputs
  | pair left right leftIH rightIH =>
    cases payload with
    | pair a b =>
      cases ha : a.eval current.ints current.bools <;> cases hb : b.eval current.ints current.bools <;>
        simp [Payload.eval, ha, hb] at known
      subst value
      exact rightIH _ _ _ (leftIH _ _ _ matchInputs ha) hb

theorem put_eval (slots : Layout τ) (payload : Payload τ) (value : Value τ) (input : Inputs)
    (known : payload.eval input.ints input.bools = some value) (term : Term sort) :
    let changed := slots.put value input
    (replace (slots.plug payload Replacement.identity) term).eval input.ints input.bools =
      term.eval changed.ints changed.bools :=
  replacement_eval _ input _ (slots.plug_reads payload value input input _ ⟨fun _ => rfl, fun _ => rfl⟩ known) term

def all : List (Term .boolean) → Term .boolean
  | [] => .bool true
  | term :: more => .and term (all more)

private theorem and_true_iff (a b : Option Bool) :
    pAnd a b = some true ↔ a = some true ∧ b = some true := by
  cases a with
  | none => cases b <;> simp [pAnd]
  | some flag => cases flag <;> simp

theorem all_true_iff (terms : List (Term .boolean)) (input : Inputs) :
    (all terms).eval input.ints input.bools = some true ↔
      ∀ t ∈ terms, t.eval input.ints input.bools = some true := by
  induction terms with
  | nil => simp [all, Term.eval]
  | cons first rest ih =>
    simp only [all, Term.eval.eq_16, and_true_iff, ih, List.mem_cons]
    exact ⟨fun ⟨a,b⟩ _ h => h.elim (fun e => e ▸ a) (b _),
      fun h => ⟨h _ (Or.inl rfl), fun _ member => h _ (Or.inr member)⟩⟩

theorem apply_implication {test consequence : Term .boolean} {input : Inputs}
    (h : (.implies test consequence : Term .boolean).eval input.ints input.bools = some true)
    (taken : test.eval input.ints input.bools = some true) :
    consequence.eval input.ints input.bools = some true := by
  simpa [Term.eval.eq_18, taken] using h

structure Policy (state result : BeamLispCore.Ty) where
  stateSlots : Layout state
  resultSlot : Layout result
  pre : Term .boolean
  inv : Term .boolean
  firstRank : Term .integer
  secondRank : Term .integer
  post : Term .boolean

structure StepTerms (state result : BeamLispCore.Ty) where
  again : Term .boolean
  value : Payload result
  next : Payload state

abbrev StepSort (state result : BeamLispCore.Ty) : BeamLispCore.Ty :=
  .prod .bool (.prod result (.prod state .unit))

def StepTerms.pack (s : StepTerms state result) : Payload (StepSort state result) :=
  .pair (.boolean s.again) (.pair s.value (.pair s.next .unit))

def StepTerms.unpack : Payload (StepSort state result) → StepTerms state result
  | .pair (.boolean again) (.pair value (.pair next .unit)) => ⟨again, value, next⟩

private theorem packed_values (data : StepTerms state result) (input : Inputs) (value : Value (StepSort state result))
    (h : data.pack.eval input.ints input.bools = some value) :
    data.again.eval input.ints input.bools = some value.1 ∧
      data.value.eval input.ints input.bools = some value.2.1 ∧
      data.next.eval input.ints input.bools = some value.2.2.1 := by
  cases a : data.again.eval input.ints input.bools <;>
    cases b : data.value.eval input.ints input.bools <;>
    cases c : data.next.eval input.ints input.bools <;> simp [StepTerms.pack, Payload.eval, a, b, c] at h
  subst value
  exact ⟨a, b, c⟩

def Policy.good (p : Policy state result) (input : Inputs) : Prop :=
  p.pre.eval input.ints input.bools = some true ∧ p.inv.eval input.ints input.bools = some true

def Policy.rank (p : Policy state result) (input : Inputs) : Int × Int :=
  ((p.firstRank.eval input.ints input.bools).getD 0, (p.secondRank.eval input.ints input.bools).getD 0)

def Policy.resultHolds (p : Policy state result) (input : Inputs) (value : Value result) : Prop :=
  let withResult := p.resultSlot.put value input
  p.post.eval withResult.ints withResult.bools = some true

def Policy.domain (p : Policy state result) : Term .boolean :=
  all [.le (.int 0) p.firstRank, .le (.int 0) p.secondRank]

def Policy.decrease (p : Policy state result) (next : Replacement) : Term .boolean :=
  let x := replace next p.firstRank
  let y := replace next p.secondRank
  .or (all [.lt x p.firstRank])
    (.or (all [.eqInt x p.firstRank, .lt y p.secondRank]) (.bool false))

def Policy.stepChecks (p : Policy state result) (stepOK : Term .boolean)
    (step : StepTerms state result) : List (Term .boolean) :=
  let next := p.stateSlots.plug step.next Replacement.identity
  let result := p.resultSlot.plug step.value Replacement.identity
  [stepOK, p.domain,
   .implies step.again (all [replace next p.pre, replace next p.inv, replace next p.domain, p.decrease next]),
   .implies (.not step.again) (replace result p.post)]

def Policy.checks (p : Policy state result) (initialOK : Term .boolean) (initial : Payload state)
    (stepOK : Term .boolean) (step : StepTerms state result) : List (Term .boolean) :=
  let start := p.stateSlots.plug initial Replacement.identity
  [initialOK, replace start p.pre, replace start p.inv,
   .implies p.inv (all (p.stepChecks stepOK step))]

def Policy.question (p : Policy state result) (initialOK : Term .boolean) (initial : Payload state)
    (stepOK : Term .boolean) (step : StepTerms state result) : Question :=
  ⟨[.bool true, p.pre], both (.bool true) (all (p.checks initialOK initial stepOK step))⟩

def initial (body : Expr context state) (env : Inputs → Env context) (slots : Layout state)
    (input : Inputs) : Except String Inputs :=
  match eval body (env input) with
  | .raised reason => .error reason
  | .returned state => .ok (slots.put state input)

def control (body : Expr context (StepSort state result)) (env : Inputs → Env context) (slots : Layout state)
    (input : Inputs) : Except String (LoopStep Inputs (Value result)) :=
  match eval body (env input) with
  | .raised reason => .error reason
  | .returned packed =>
    if packed.1 then .ok (.again (slots.put packed.2.2.1 input)) else .ok (.finished packed.2.1)

private theorem domain_values (p : Policy state result) (input : Inputs)
    (h : p.domain.eval input.ints input.bools = some true) :
    p.firstRank.eval input.ints input.bools = some (p.rank input).1 ∧
      p.secondRank.eval input.ints input.bools = some (p.rank input).2 ∧
      0 ≤ (p.rank input).1 ∧ 0 ≤ (p.rank input).2 := by
  have checks := (all_true_iff _ input).mp h
  have hx := checks (.le (.int 0) p.firstRank) (by simp [Policy.domain])
  have hy := checks (.le (.int 0) p.secondRank) (by simp [Policy.domain])
  cases x : p.firstRank.eval input.ints input.bools <;>
    cases y : p.secondRank.eval input.ints input.bools <;> simp [Term.eval.eq_11, Term.eval.eq_1, x, y] at hx hy
  exact ⟨rfl, rfl, hx, hy⟩

private theorem checked_decrease (p : Policy state result) (r : Replacement) (current next : Inputs)
    (matching : reads r current next)
    (domain : p.domain.eval current.ints current.bools = some true)
    (nextDomain : p.domain.eval next.ints next.bools = some true)
    (h : (p.decrease r).eval current.ints current.bools = some true) :
    decreases (p.rank next) (p.rank current) := by
  obtain ⟨x, y, _, _⟩ := domain_values p current domain
  obtain ⟨x', y', _, _⟩ := domain_values p next nextDomain
  simpa [Policy.decrease, decreases, all, Term.eval.eq_1, Term.eval.eq_2, Term.eval.eq_12,
    Term.eval.eq_13, Term.eval.eq_16, Term.eval.eq_17, replacement_eval r current next matching, x, y, x', y'] using h

private theorem checked_terms (p : Policy state result) (initialOK : Term .boolean) (start : Payload state)
    (stepOK : Term .boolean) (step : StepTerms state result)
    (checked : (p.question initialOK start stepOK step).entails) (input : Inputs)
    (pre : p.pre.eval input.ints input.bools = some true) :
    ∀ term ∈ p.checks initialOK start stepOK step, term.eval input.ints input.bools = some true := by
  apply (all_true_iff _ input).mp
  have claim := checked input.ints input.bools (by
    intro t member
    simp only [Policy.question, List.mem_cons, List.not_mem_nil, or_false] at member
    rcases member with a | b
    · subst t; rfl
    · subst t; exact pre)
  simpa [Policy.question, both, Term.eval.eq_2, Term.eval.eq_16] using claim

#print axioms replacement_eval
#print axioms Layout.plug_reads
#print axioms put_eval
#print axioms domain_values
#print axioms checked_decrease
end CoreLoop
