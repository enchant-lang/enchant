import Std

/- Ordered, total integer choice bindings have a unique extension. This model
   does not establish correspondence with the BL graph transformer, its string
   names, graph encoding, resource policy, Source interpretation or compiler. -/
namespace FormalChoiceExtension

abbrev Store := List Int

structure Binding where
  guard : Store → Bool
  yes : Store → Int
  no : Store → Int

def Binding.value (binding : Binding) (store : Store) : Int :=
  if binding.guard store = true then binding.yes store else binding.no store

def Binding.holds (binding : Binding) (store : Store) (value : Int) : Prop :=
  (binding.guard store = true → value = binding.yes store) ∧
  (binding.guard store = false → value = binding.no store)

theorem guarded_eq_choice (binding : Binding) (store : Store) (value : Int) :
    binding.holds store value ↔ value = binding.value store := by
  cases h : binding.guard store <;> simp [Binding.holds, Binding.value, h]

theorem choice_guarded (binding : Binding) (store : Store) :
    binding.holds store (binding.value store) :=
  (guarded_eq_choice binding store _).mpr rfl

theorem guarded_unique (binding : Binding) (store : Store) (a b : Int)
    (ha : binding.holds store a) (hb : binding.holds store b) : a = b :=
  ((guarded_eq_choice binding store a).mp ha).trans
    ((guarded_eq_choice binding store b).mp hb).symm

def run : List Binding → Store → Store
  | [], store => store
  | binding :: rest, store => run rest (binding.value store :: store)

inductive Defines : List Binding → Store → Store → Prop where
  | done (store : Store) : Defines [] store store
  | step (binding : Binding) (rest : List Binding) (store : Store)
      (value : Int) (finish : Store)
      (head : binding.holds store value)
      (tail : Defines rest (value :: store) finish) :
      Defines (binding :: rest) store finish

theorem run_defines (bindings : List Binding) (store : Store) :
    Defines bindings store (run bindings store) := by
  induction bindings generalizing store with
  | nil => exact Defines.done store
  | cons binding rest ih =>
    exact Defines.step binding rest store (binding.value store)
      (run rest (binding.value store :: store)) (choice_guarded binding store) (ih _)

theorem defines_result {bindings : List Binding} {store finish : Store}
    (defined : Defines bindings store finish) : finish = run bindings store := by
  induction defined with
  | done store => rfl
  | step binding rest store value finish head tail ih =>
    have value_eq := (guarded_eq_choice binding store value).mp head
    simpa only [run, value_eq] using ih

theorem defines_iff_run (bindings : List Binding) (store finish : Store) :
    Defines bindings store finish ↔ finish = run bindings store := by
  constructor
  · exact defines_result
  · intro equal
    subst finish
    exact run_defines bindings store

theorem unique_extension (bindings : List Binding) (store : Store) :
    ∃ finish, Defines bindings store finish ∧
      ∀ other, Defines bindings store other → other = finish := by
  exact ⟨run bindings store, run_defines bindings store, fun _ h => defines_result h⟩

theorem extension_length (bindings : List Binding) (store : Store) :
    (run bindings store).length = bindings.length + store.length := by
  induction bindings generalizing store with
  | nil => simp [run]
  | cons binding rest ih => simp [run, ih, Nat.add_comm, Nat.add_left_comm]

theorem extension_prefix (bindings : List Binding) (store : Store) :
    ∃ generated, generated.length = bindings.length ∧
      run bindings store = generated ++ store := by
  induction bindings generalizing store with
  | nil => exact ⟨[], rfl, rfl⟩
  | cons binding rest ih =>
    obtain ⟨generated, length_eq, result_eq⟩ := ih (binding.value store :: store)
    refine ⟨generated ++ [binding.value store], ?_, ?_⟩
    · simp [length_eq]
    · simpa [run, List.append_assoc] using result_eq

theorem existential_projection (bindings : List Binding) (store : Store)
    (property : Store → Prop) :
    (∃ finish, Defines bindings store finish ∧ property finish) ↔
      property (run bindings store) := by
  constructor
  · rintro ⟨finish, defined, h⟩
    simpa only [defines_result defined] using h
  · intro h
    exact ⟨run bindings store, run_defines bindings store, h⟩

theorem universal_projection (bindings : List Binding) (store : Store)
    (property : Store → Prop) :
    (∀ finish, Defines bindings store finish → property finish) ↔
      property (run bindings store) := by
  constructor
  · intro h
    exact h _ (run_defines bindings store)
  · intro h finish defined
    simpa only [defines_result defined] using h

theorem counterexample_projection (bindings : List Binding) (store : Store)
    (property : Store → Bool) :
    property (run bindings store) = false ↔
      ∃ finish, Defines bindings store finish ∧ property finish = false :=
  (existential_projection bindings store (fun finish => property finish = false)).symm

theorem premise_feasibility {Input : Type} (bindings : List Binding)
    (initial : Input → Store) (premise : Input → Prop) :
    (∃ input, premise input) ↔
      ∃ input finish, premise input ∧ Defines bindings (initial input) finish := by
  constructor
  · rintro ⟨input, h⟩
    exact ⟨input, run bindings (initial input), h, run_defines _ _⟩
  · rintro ⟨input, finish, h, _⟩
    exact ⟨input, h⟩

theorem conditional_transfer {Input : Type} (bindings : List Binding)
    (initial : Input → Store) (premise : Input → Prop) (property : Input → Store → Prop)
    (derived : ∀ input finish, premise input → Defines bindings (initial input) finish → property input finish) :
    ∀ input, premise input → property input (run bindings (initial input)) := by
  intro input h
  exact derived input _ h (run_defines _ _)

/- The original/target evaluator relation is an explicit premise. The theorem
   below cannot manufacture that implementation connection from a target proof. -/
theorem original_entailment {Input : Type} (bindings : List Binding)
    (initial : Input → Store) (premise original : Input → Prop)
    (target : Input → Store → Prop)
    (connection : ∀ input, original input ↔ target input (run bindings (initial input)))
    (derived : ∀ input finish, premise input → Defines bindings (initial input) finish → target input finish) :
    ∀ input, premise input → original input := by
  intro input h
  exact (connection input).mpr (conditional_transfer bindings initial premise target derived input h)

#print axioms guarded_eq_choice
#print axioms choice_guarded
#print axioms guarded_unique
#print axioms run_defines
#print axioms defines_result
#print axioms defines_iff_run
#print axioms unique_extension
#print axioms extension_length
#print axioms extension_prefix
#print axioms existential_projection
#print axioms universal_projection
#print axioms counterexample_projection
#print axioms premise_feasibility
#print axioms conditional_transfer
#print axioms original_entailment

end FormalChoiceExtension
