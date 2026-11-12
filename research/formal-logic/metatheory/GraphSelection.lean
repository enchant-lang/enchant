import GraphTable

/- Selective interpretation over the previously qualified structural model.
   This candidate is not yet qualified. It does not model BL atom admission,
   container reconstruction, resource checks, canonical bytes or compiler code. -/
namespace FormalGraphTable
set_option autoImplicit false
variable {size : Nat} {α : Type}

/-- Finite, constructive sequencing; a missing child refuses the container. -/
def sequenceFin : {n : Nat} → (Fin n → Option α) → Option (Fin n → α)
  | 0, _ => some (fun index => Fin.elim0 index)
  | n + 1, values => do
    let previous ← sequenceFin (fun i => values i.castSucc)
    let latest ← values (Fin.last n)
    pure (extend previous latest)

theorem sequenceFin_some {n : Nat} (values : Fin n → α) :
    sequenceFin (fun i => some (values i)) = some values := by
  induction n with
  | zero => rfl
  | succ n ih =>
    simp only [sequenceFin, ih]
    congr 1
    funext index
    by_cases earlier : index.val < n
    · simp [extend, earlier]
    · have last : index = Fin.last n := by apply Fin.ext; simp [Fin.last]; omega
      subst index
      simp [extend]

def Kind.sequence (kind : Kind) (values : kind.Slot → Option α) : Option (kind.Slot → α) :=
  match kind with
  | .vector _ | .list _ | .set _ | .tuple _ => sequenceFin values
  | .map _ => do
    let pairs ← sequenceFin (fun i => do
      let key ← values (i, false)
      let value ← values (i, true)
      pure (key, value))
    pure (fun slot => if slot.2 then (pairs slot.1).2 else (pairs slot.1).1)

theorem sequence_some (kind : Kind) (values : kind.Slot → α) :
    kind.sequence (fun slot => some (values slot)) = some values := by
  cases kind with
  | vector n => exact sequenceFin_some values
  | list n => exact sequenceFin_some values
  | set n => exact sequenceFin_some values
  | tuple n => exact sequenceFin_some values
  | map n =>
    simp only [Kind.sequence, Option.bind_some]
    rw [sequenceFin_some]
    simp only [Option.bind_some]
    congr 1
    funext slot
    rcases slot with ⟨index, side⟩
    cases side <;> rfl

def Row.partialApply (leaf : Scalar → Option α) (node : Algebra α)
    (previous : Fin size → Option α) : Row size → Option α
  | .scalar value => leaf value
  | .node kind children => (kind.sequence (fun slot => previous (children slot))).map (node kind)

/-- Readiness concerns a demanded row only: admitted scalar or demanded children. -/
def Row.Ready (leaf : Scalar → Option α) (fullLeaf : Scalar → α)
    (wanted : Fin size → Bool) : Row size → Prop
  | .scalar value => leaf value = some (fullLeaf value)
  | .node _ children => ∀ slot, wanted (children slot) = true

theorem partial_apply_agrees (leaf : Scalar → Option α) (fullLeaf : Scalar → α)
    (node : Algebra α) (wanted : Fin size → Bool) (values : Fin size → Option α)
    (full : Fin size → α) (row : Row size)
    (ready : row.Ready leaf fullLeaf wanted)
    (agree : ∀ i, wanted i = true → values i = some (full i)) :
    row.partialApply leaf node values = some (row.apply fullLeaf node full) := by
  cases row with
  | scalar value => exact ready
  | node kind children =>
    have selected : (fun slot => values (children slot)) = (fun slot => some (full (children slot))) := by
      funext slot
      exact agree (children slot) (ready slot)
    simp only [Row.partialApply, selected, sequence_some, Option.map_some, Row.apply]

def Table.partialFold (leaf : Scalar → Option α) (node : Algebra α) :
    {size : Nat} → Table size → (Fin size → Bool) → Fin size → Option α
  | _, .empty, _ => fun index => Fin.elim0 index
  | _, .push previous row, wanted =>
    let values := previous.partialFold leaf node (fun i => wanted i.castSucc)
    extend values (if wanted (Fin.last _) then row.partialApply leaf node values else none)

def Table.Ready (leaf : Scalar → Option α) (fullLeaf : Scalar → α) :
    {size : Nat} → Table size → (Fin size → Bool) → Prop
  | _, .empty, _ => True
  | _, .push previous row, wanted =>
    previous.Ready leaf fullLeaf (fun i => wanted i.castSucc) ∧
      (wanted (Fin.last _) = true → row.Ready leaf fullLeaf (fun i => wanted i.castSucc))

theorem selective_fold_agrees (leaf : Scalar → Option α) (fullLeaf : Scalar → α)
    (node : Algebra α) (table : Table size) (wanted : Fin size → Bool)
    (ready : table.Ready leaf fullLeaf wanted) :
    ∀ index, wanted index = true →
      table.partialFold leaf node wanted index = some (table.fold fullLeaf node index) := by
  induction table with
  | empty => intro index; exact Fin.elim0 index
  | @push n previous row ih =>
    intro index needed
    by_cases earlier : index.val < n
    · have prefixNeeded : wanted (⟨index.val, earlier⟩ : Fin n).castSucc = true := by
        simpa using needed
      simpa only [Table.partialFold, Table.fold, extend, dite_eq_left earlier] using
        ih (fun i => wanted i.castSucc) ready.1 ⟨index.val, earlier⟩ prefixNeeded
    · have last : index = Fin.last n := by apply Fin.ext; simp [Fin.last]; omega
      subst index
      simp only [Table.partialFold, Table.fold, extend_last, needed, Bool.true_eq, if_true]
      exact partial_apply_agrees leaf fullLeaf node (fun i => wanted i.castSucc)
        _ _ row (ready.2 needed) (ih _ ready.1)

theorem unselected_is_none (leaf : Scalar → Option α) (node : Algebra α)
    (table : Table size) (wanted : Fin size → Bool) (index : Fin size)
    (unneeded : wanted index = false) :
    table.partialFold leaf node wanted index = none := by
  induction table with
  | empty => exact Fin.elim0 index
  | @push n previous row ih =>
    by_cases earlier : index.val < n
    · have prefixUnneeded : wanted (⟨index.val, earlier⟩ : Fin n).castSucc = false := by
        simpa using unneeded
      simpa only [Table.partialFold, extend, dite_eq_left earlier] using
        ih (fun i => wanted i.castSucc) ⟨index.val, earlier⟩ prefixUnneeded
    · have last : index = Fin.last n := by apply Fin.ext; simp [Fin.last]; omega
      subst index
      simp [Table.partialFold, unneeded]

theorem selective_interpretation_agrees (leaf : Scalar → Option Value)
    (table : Table size) (wanted : Fin size → Bool)
    (ready : table.Ready leaf Value.scalar wanted) (index : Fin size)
    (needed : wanted index = true) :
    table.partialFold leaf Value.node wanted index = some (interpret table index) :=
  selective_fold_agrees leaf Value.scalar Value.node table wanted ready index needed

theorem selected_interpretations_agree (left right : Scalar → Option Value)
    (table : Table size) (leftMask rightMask : Fin size → Bool)
    (leftReady : table.Ready left Value.scalar leftMask)
    (rightReady : table.Ready right Value.scalar rightMask) (index : Fin size)
    (leftNeeded : leftMask index = true) (rightNeeded : rightMask index = true) :
    table.partialFold left Value.node leftMask index =
      table.partialFold right Value.node rightMask index := by
  rw [selective_interpretation_agrees left table leftMask leftReady index leftNeeded,
      selective_interpretation_agrees right table rightMask rightReady index rightNeeded]

#print axioms sequenceFin_some
#print axioms sequence_some
#print axioms partial_apply_agrees
#print axioms selective_fold_agrees
#print axioms unselected_is_none
#print axioms selective_interpretation_agrees
#print axioms selected_interpretations_agree
end FormalGraphTable
