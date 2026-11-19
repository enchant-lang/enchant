/- A compiler operation with a deterministic continuation can consult a key
   chosen using earlier outcomes. `none` records a miss with the same weight
   as a hit. The model requires every relevant input or effect to be visible
   through a consultation or fixed outside the operation. -/
namespace NativeLinkReplay

inductive Computation (Key Value Result : Type) where
  | done (result : Result)
  | consult (key : Key) (next : Option Value → Computation Key Value Result)

def run (lookup : Key → Option Value) : Computation Key Value Result → Result
  | .done result => result
  | .consult key next => run lookup (next (lookup key))

def consulted (lookup : Key → Option Value) : Computation Key Value Result → List Key
  | .done _ => []
  | .consult key next => key :: consulted lookup (next (lookup key))

theorem replay (old new : Key → Option Value) (computation : Computation Key Value Result)
    (agree : ∀ key ∈ consulted old computation, new key = old key) :
    run new computation = run old computation ∧
      consulted new computation = consulted old computation := by
  induction computation with
  | done result => exact ⟨rfl, rfl⟩
  | consult key next ih =>
    have head : new key = old key := agree key (by simp [consulted])
    have tail : ∀ k ∈ consulted old (next (old key)), new k = old k := by
      intro k member
      exact agree k (by simp [consulted, member])
    obtain ⟨sameResult, sameKeys⟩ := ih (old key) tail
    exact ⟨by simpa only [run, head] using sameResult,
           by simp only [consulted, head, sameKeys]⟩

#print axioms replay

section OrderedEffects

variable {Key Value Result : Type} [DecidableEq Key]

inductive Event (Key Value : Type) where
  | read (key : Key) (outcome : Option Value)
  | write (key : Key) (value : Option Value)

inductive Staging (Key Value Result : Type) where
  | done (result : Result)
  | consult (key : Key) (next : Option Value → Staging Key Value Result)
  | publish (key : Key) (value : Option Value) (next : Staging Key Value Result)

def replace (state : Key → Option Value) (key : Key) (value : Option Value) : Key → Option Value :=
  fun candidate => if candidate = key then value else state candidate

def execute (state : Key → Option Value) : Staging Key Value Result → Result × List (Event Key Value)
  | .done result => (result, [])
  | .consult key next =>
    let outcome := state key
    let (result, events) := execute state (next outcome)
    (result, .read key outcome :: events)
  | .publish key value next =>
    let (result, events) := execute (replace state key value) next
    (result, .write key value :: events)

def valid (state : Key → Option Value) : List (Event Key Value) → Prop
  | [] => True
  | .read key outcome :: tail => state key = outcome ∧ valid state tail
  | .write key value :: tail => valid (replace state key value) tail

theorem replayOrdered (old new : Key → Option Value) (program : Staging Key Value Result)
    (checks : valid new (execute old program).2) : execute new program = execute old program := by
  induction program generalizing old new with
  | done result => rfl
  | consult key next ih =>
    have readAndTail : new key = old key ∧ valid new (execute old (next (old key))).2 := by
      simpa [execute, valid] using checks
    have tail := ih (old key) old new readAndTail.2
    simp [execute, readAndTail.1, tail]
  | publish key value next ih =>
    have tailChecks : valid (replace new key value) (execute (replace old key value) next).2 := by
      simpa [execute, valid] using checks
    simp [execute, ih (replace old key value) (replace new key value) tailChecks]

#print axioms replayOrdered

def inputKeys : List (Event Key Value) → List Key
  | [] => []
  | .read key _ :: tail => key :: inputKeys tail
  | .write key _ :: tail => (inputKeys tail).filter (fun candidate => decide (candidate ≠ key))

theorem validIffInputKeys (receipt : List (Event Key Value)) (old new : Key → Option Value)
    (baseline : valid old receipt) : valid new receipt ↔ ∀ key ∈ inputKeys receipt, new key = old key := by
  induction receipt generalizing old new with
  | nil => simp [valid, inputKeys]
  | cons event tail ih =>
    cases event with
    | read key outcome =>
      simp only [valid] at baseline ⊢
      rw [ih old new baseline.2]
      constructor
      · intro agrees candidate member
        simp only [inputKeys, List.mem_cons] at member
        rcases member with same | later
        · subst candidate
          exact agrees.1.trans baseline.1.symm
        · exact agrees.2 candidate later
      · intro agrees
        exact ⟨(agrees key (by simp [inputKeys])).trans baseline.1,
               fun candidate member => agrees candidate (by simp [inputKeys, member])⟩
    | write key outcome =>
      simp only [valid] at baseline ⊢
      rw [ih (replace old key outcome) (replace new key outcome) baseline]
      constructor
      · intro agrees candidate member
        have selected := List.mem_filter.mp (by simpa only [inputKeys] using member)
        have distinct : candidate ≠ key := of_decide_eq_true selected.2
        simpa [replace, distinct] using agrees candidate selected.1
      · intro agrees candidate member
        by_cases same : candidate = key
        · simp [replace, same]
        · have selected : candidate ∈ inputKeys (.write key outcome :: tail) := by
            simp [inputKeys, same, member]
          simpa [replace, same] using agrees candidate selected

#print axioms validIffInputKeys

theorem executeValid (state : Key → Option Value) (program : Staging Key Value Result) :
    valid state (execute state program).2 := by
  induction program generalizing state with
  | done result => trivial
  | consult key next ih =>
    simpa [execute, valid] using ih (state key) state
  | publish key value next ih =>
    simpa [execute, valid] using ih (replace state key value)

/- A private scope can install a subset of its initial rows if every observed
   pre-write hit is kept. Initial misses stay misses, and the computation's
   own publications still override the initial table. -/
theorem replayWithInitialSubset (state : Key → Option Value)
    (program : Staging Key Value Result) (keep : Key → Bool)
    (coversHits : ∀ key ∈ inputKeys (execute state program).2,
      keep key = true ∨ state key = none) :
    execute (fun key => if keep key then state key else none) program =
      execute state program := by
  apply replayOrdered
  apply (validIffInputKeys _ state _ (executeValid state program)).mpr
  intro key read
  rcases coversHits key read with kept | absent
  · simp [kept]
  · simp [absent]

#print axioms replayWithInitialSubset

/- Check the trace obtained from the subset against the full candidate table.
   The full-table trace need not be available to verify the subset run. A
   candidate hit at any omitted pre-write key invalidates this certificate. -/
theorem verifySubsetAgainstFull (state : Key → Option Value)
    (program : Staging Key Value Result) (keep : Key → Bool)
    (coversHits : ∀ key ∈ inputKeys (execute (fun k => if keep k then state k else none) program).2,
      keep key = true ∨ state key = none) :
    execute state program =
      execute (fun key => if keep key then state key else none) program := by
  apply replayOrdered
  apply (validIffInputKeys _ _ state (executeValid _ program)).mpr
  intro key read
  rcases coversHits key read with kept | absent
  · simp [kept]
  · simp [absent]

#print axioms verifySubsetAgainstFull

/- Once the sparse stage trace verifies against the complete initial table,
   a checked lowering receipt can act on its prepared result. The lowering
   equality is independent evidence about the admitted compiler inputs. -/
theorem reuseAfterGuardedStage {Unit : Type} (state : Key → Option Value)
    (stage : Staging Key Value Result) (keep : Key → Bool) (lower : Result → Unit)
    (donorInput : Result) (donorUnit : Unit)
    (coversHits : ∀ key ∈ inputKeys (execute (fun k => if keep k then state k else none) stage).2,
      keep key = true ∨ state key = none)
    (samePrepared : (execute (fun k => if keep k then state k else none) stage).1 = donorInput)
    (loweringChecked : lower donorInput = donorUnit) :
    lower (execute state stage).1 = donorUnit := by
  rw [verifySubsetAgainstFull state stage keep coversHits, samePrepared]
  exact loweringChecked

#print axioms reuseAfterGuardedStage

def externalWrites (external : Key → Bool) : List (Event Key Value) → List (Key × Option Value)
  | [] => []
  | .read _ _ :: tail => externalWrites external tail
  | .write key value :: tail =>
      if external key then (key, value) :: externalWrites external tail
      else externalWrites external tail

/- An isolated member may reuse a checked unit without applying a staging
   effect only when the validated trace's external publications are empty.
   The runtime must establish that its trace accounts for every effect and
   that the saved unit comes from the checked lowering. -/
theorem resumeClosedMember {Unit : Type} (old current : Key → Option Value)
    (stage : Staging Key Value Result) (lower : Result → Unit)
    (external : Key → Bool) (saved : Unit)
    (stagingChecked : valid current (execute old stage).2)
    (closed : externalWrites external (execute old stage).2 = [])
    (loweringChecked : lower (execute old stage).1 = saved) :
    (lower (execute current stage).1, externalWrites external (execute current stage).2) =
      (saved, []) := by
  rw [replayOrdered old current stage stagingChecked, loweringChecked, closed]

omit [DecidableEq Key] in
theorem externalPublicationIneligible (external : Key → Bool) (key : Key) (value : Option Value)
    (tail : List (Event Key Value)) (visible : external key = true) :
    externalWrites external (.write key value :: tail) ≠ [] := by
  simp [externalWrites, visible]

#print axioms resumeClosedMember
#print axioms externalPublicationIneligible

section ReverseIndex

variable {Member : Type}

def affected (consumers : Key → List Member) (changed : List Key) : List Member :=
  changed.flatMap consumers

theorem replayUnaffected [DecidableEq Value] (unit : Member)
    (consumers : Key → List Member) (changed : List Key)
    (old new : Key → Option Value) (program : Staging Key Value Result)
    (indexComplete : ∀ key ∈ inputKeys (execute old program).2, unit ∈ consumers key)
    (changesComplete : ∀ key, new key ≠ old key → key ∈ changed)
    (unaffected : unit ∉ affected consumers changed) :
    execute new program = execute old program := by
  apply replayOrdered
  apply (validIffInputKeys _ old new (executeValid old program)).mpr
  intro key read
  by_cases equal : new key = old key
  · exact equal
  · exact False.elim (unaffected (List.mem_flatMap.mpr ⟨key, changesComplete key equal,
      indexComplete key read⟩))

#print axioms replayUnaffected

end ReverseIndex

end OrderedEffects

section SnapshotReads

variable {Key Value : Type}

def agreesWithReads (state : Key → Value) (reads : List (Key × Value)) : Prop :=
  ∀ key value, (key, value) ∈ reads → state key = value

theorem conflictingReadsRejectSnapshot (reads : List (Key × Value)) (state : Key → Value)
    (key : Key) (first second : Value)
    (firstRead : (key, first) ∈ reads) (secondRead : (key, second) ∈ reads)
    (different : first ≠ second) : ¬ agreesWithReads state reads := by
  intro agrees
  exact different ((agrees key first firstRead).symm.trans (agrees key second secondRead))

theorem checkEachReadKeyOnce (reads : List (Key × Value)) (captured : Key → Option Value)
    (state : Key → Value)
    (exactCoverage : ∀ key value, (key, value) ∈ reads ↔ captured key = some value) :
    agreesWithReads state reads ↔ ∀ key value, captured key = some value → state key = value := by
  constructor
  · intro agrees key value recorded
    exact agrees key value ((exactCoverage key value).mpr recorded)
  · intro agrees key value observed
    exact agrees key value ((exactCoverage key value).mp observed)

-- An observed negative Boolean remains an input. None means no observation.
example (key : Key) (state : Key → Bool) (ready : state key = true) :
    ¬ agreesWithReads state [(key, false)] := by
  intro agrees
  have missing := agrees key false (by simp)
  rw [ready] at missing
  contradiction

#print axioms conflictingReadsRejectSnapshot
#print axioms checkEachReadKeyOnce

end SnapshotReads

end NativeLinkReplay
