import Std

/- A structural model, not a theorem about the BL implementation, canonical
   bytes, SHA-256, Unicode admission, runtime keyword admission, map/set key
   policy, typed binders, native execution, or compiler preservation.

   Every appended row refers only to the existing finite prefix. Interpretation
   is total by construction. Scalars retain tags and exact payloads; map slots
   are explicit ordered entry/key-or-value pairs, not a host map's equality. -/
namespace FormalGraphTable
set_option autoImplicit false
variable {size before after : Nat}

inductive Scalar where
  | nil
  | boolean (value : Bool)
  | integer (value : Int)
  | float64 (bits : Fin (2 ^ 64))
  | bytes (value : List UInt8)
  | keyword (name : List UInt8)
  | symbol (name : List UInt8)
  deriving DecidableEq, Repr

inductive Kind where
  | vector (size : Nat)
  | list (size : Nat)
  | set (size : Nat)
  | tuple (size : Nat)
  | map (entries : Nat)
  deriving DecidableEq, Repr

def Kind.Slot : Kind → Type
  | .vector size | .list size | .set size | .tuple size => Fin size
  | .map entries => Fin entries × Bool

def Kind.slots : (kind : Kind) → List kind.Slot
  | .vector size | .list size | .set size | .tuple size => List.finRange size
  | .map entries => (List.finRange entries).flatMap (fun i => [(i, false), (i, true)])

theorem slots_complete (kind : Kind) (slot : kind.Slot) : slot ∈ kind.slots := by
  cases kind with
  | vector size => exact List.mem_finRange slot
  | list size => exact List.mem_finRange slot
  | set size => exact List.mem_finRange slot
  | tuple size => exact List.mem_finRange slot
  | map entries =>
    rcases slot with ⟨index, side⟩
    apply List.mem_flatMap.mpr
    exact ⟨index, List.mem_finRange index, by cases side <;> simp⟩

inductive Value where
  | scalar (value : Scalar)
  | node (kind : Kind) (children : kind.Slot → Value)

abbrev Algebra (α : Type) := (kind : Kind) → (kind.Slot → α) → α

def Value.fold {α : Type} (leaf : Scalar → α) (node : Algebra α) : Value → α
  | .scalar value => leaf value
  | .node kind children => node kind (fun slot => Value.fold leaf node (children slot))

@[simp] theorem fold_scalar {α : Type} (leaf : Scalar → α) (node : Algebra α) (s : Scalar) :
    Value.fold leaf node (.scalar s) = leaf s := rfl
@[simp] theorem fold_node {α : Type} (leaf : Scalar → α) (node : Algebra α)
    (kind : Kind) (children : kind.Slot → Value) :
    Value.fold leaf node (.node kind children) =
      node kind (fun slot => Value.fold leaf node (children slot)) := rfl

inductive Row (size : Nat) where
  | scalar (value : Scalar)
  | node (kind : Kind) (children : kind.Slot → Fin size)

def Row.apply {α : Type} (leaf : Scalar → α) (node : Algebra α)
    (previous : Fin size → α) : Row size → α
  | .scalar s => leaf s
  | .node kind children => node kind (fun slot => previous (children slot))

def Row.rename (rename : Fin before → Fin after) : Row before → Row after
  | .scalar s => .scalar s
  | .node kind children => .node kind (fun slot => rename (children slot))

theorem apply_rename {α : Type} (leaf : Scalar → α) (node : Algebra α)
    (values : Fin after → α) (rename : Fin before → Fin after) (row : Row before) :
    Row.apply leaf node values (row.rename rename) =
      Row.apply leaf node (fun i => values (rename i)) row := by
  cases row <;> rfl

inductive Table : Nat → Type where
  | empty : Table 0
  | push {size : Nat} (previous : Table size) (row : Row size) : Table (size + 1)

def extend {α : Type} (previous : Fin size → α) (latest : α) : Fin (size + 1) → α :=
  fun index => if h : index.val < size then previous ⟨index.val, h⟩ else latest

@[simp] theorem extend_old {α : Type} (previous : Fin size → α) (latest : α) (i : Fin size) :
    extend previous latest i.castSucc = previous i := by
  simp [extend, i.isLt]
@[simp] theorem extend_last {α : Type} (previous : Fin size → α) (latest : α) :
    extend previous latest (Fin.last size) = latest := by
  simp [extend, Fin.last]

def Table.fold {α : Type} (leaf : Scalar → α) (node : Algebra α) :
    {size : Nat} → Table size → Fin size → α
  | _, .empty => fun index => Fin.elim0 index
  | _, .push previous row =>
    let values := Table.fold leaf node previous
    extend values (Row.apply leaf node values row)

@[simp] theorem fold_push_old {α : Type} (leaf : Scalar → α) (node : Algebra α)
    (previous : Table size) (row : Row size) (i : Fin size) :
    Table.fold leaf node (.push previous row) i.castSucc = Table.fold leaf node previous i := by
  simp [Table.fold]
@[simp] theorem fold_push_last {α : Type} (leaf : Scalar → α) (node : Algebra α)
    (previous : Table size) (row : Row size) :
    Table.fold leaf node (.push previous row) (Fin.last size) =
      Row.apply leaf node (Table.fold leaf node previous) row := by
  simp [Table.fold]

def interpret (table : Table size) : Fin size → Value :=
  Table.fold Value.scalar Value.node table

theorem interpretation_preserves_prefix (previous : Table size) (row : Row size) (i : Fin size) :
    interpret (.push previous row) i.castSucc = interpret previous i := by
  simp [interpret]

theorem table_fold_fusion {α : Type} (leaf : Scalar → α) (node : Algebra α)
    (table : Table size) :
    ∀ index, Value.fold leaf node (interpret table index) = Table.fold leaf node table index := by
  induction table with
  | empty => intro index; exact Fin.elim0 index
  | @push size previous row ih =>
    intro index
    by_cases earlier : index.val < size
    · simpa only [interpret, Table.fold, extend, dif_pos earlier] using ih ⟨index.val, earlier⟩
    · cases row with
      | scalar value => simp [interpret, Table.fold, extend, earlier, Row.apply]
      | node kind children =>
        simp only [interpret, Table.fold, extend, dif_neg earlier, Row.apply, fold_node]
        apply congrArg (node kind)
        funext slot
        exact ih (children slot)

def sumChildren (kind : Kind) (children : kind.Slot → Nat) : Nat :=
  (kind.slots.map children).foldl (fun total value => total + value) 0

def nodeCountAlgebra : Algebra Nat := fun kind children => 1 + sumChildren kind children

def Value.expandedNodes : Value → Nat := Value.fold (fun _ => 1) nodeCountAlgebra
def Table.expandedNodes (table : Table size) : Fin size → Nat :=
  Table.fold (fun _ => 1) nodeCountAlgebra table

theorem expanded_node_count_agrees (table : Table size) (index : Fin size) :
    (interpret table index).expandedNodes = table.expandedNodes index :=
  table_fold_fusion (fun _ => 1) nodeCountAlgebra table index

def Value.scalarCost (cost : Scalar → Nat) : Value → Nat :=
  Value.fold cost sumChildren
def Table.scalarCost (cost : Scalar → Nat) (table : Table size) : Fin size → Nat :=
  Table.fold cost sumChildren table

theorem expanded_scalar_cost_agrees (cost : Scalar → Nat) (table : Table size) (index : Fin size) :
    Value.scalarCost cost (interpret table index) = Table.scalarCost cost table index :=
  table_fold_fusion cost sumChildren table index

def heightAlgebra : Algebra Nat := fun kind children =>
  if kind.slots.isEmpty then 0 else
    1 + (kind.slots.map children).foldl Nat.max 0

def Value.height : Value → Nat := Value.fold (fun _ => 0) heightAlgebra
def Table.height (table : Table size) : Fin size → Nat :=
  Table.fold (fun _ => 0) heightAlgebra table

theorem height_agrees (table : Table size) (index : Fin size) :
    (interpret table index).height = table.height index :=
  table_fold_fusion (fun _ => 0) heightAlgebra table index

theorem checked_expansion_bound (table : Table size) (index : Fin size) (limit : Nat)
    (within : table.expandedNodes index ≤ limit) :
    (interpret table index).expandedNodes ≤ limit := by
  rw [expanded_node_count_agrees]
  exact within

#print axioms slots_complete
#print axioms apply_rename
#print axioms interpretation_preserves_prefix
#print axioms table_fold_fusion
#print axioms expanded_node_count_agrees
#print axioms expanded_scalar_cost_agrees
#print axioms height_agrees
#print axioms checked_expansion_bound
end FormalGraphTable
