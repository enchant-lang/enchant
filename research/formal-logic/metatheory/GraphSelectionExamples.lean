import GraphSelection
namespace FormalGraphTable.SelectionExamples
set_option autoImplicit false

def known : Scalar := .integer 7
def unfamiliar : Scalar := .keyword [103, 114, 97, 112, 104, 46, 117, 110, 107, 110, 111, 119, 110]
def table : Table 3 :=
  .push (.push (.push .empty (.scalar known)) (.scalar unfamiliar))
    (.node (.vector 2) (fun slot => slot))

def admit : Scalar → Option Value
  | .keyword _ => none
  | scalar => some (.scalar scalar)

def selected : Fin 3 → Bool := fun index => index.val == 0
def everything : Fin 3 → Bool := fun _ => true

theorem selected_ready : table.Ready admit Value.scalar selected := by
  refine ⟨⟨⟨True.intro, ?_⟩, ?_⟩, ?_⟩
  · intro _; rfl
  · intro impossible; cases impossible
  · intro impossible; cases impossible

theorem selected_integer_preserved :
    table.partialFold admit Value.node selected ⟨0, by decide⟩ = some (.scalar (.integer 7)) := by
  rfl

theorem unrelated_keyword_skipped :
    table.partialFold admit Value.node selected ⟨1, by decide⟩ = none := by
  rfl

theorem full_materialization_refuses :
    table.partialFold admit Value.node everything ⟨2, by decide⟩ = none := by
  rfl

theorem selection_connects_original :
    table.partialFold admit Value.node selected ⟨0, by decide⟩ =
      some (interpret table ⟨0, by decide⟩) :=
  selective_interpretation_agrees admit table selected selected_ready _ (by rfl)

#print axioms selected_ready
#print axioms selected_integer_preserved
#print axioms unrelated_keyword_skipped
#print axioms full_materialization_refuses
#print axioms selection_connects_original
end FormalGraphTable.SelectionExamples
