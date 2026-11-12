import GraphSelectionExamples
open FormalGraphTable FormalGraphTable.SelectionExamples
theorem incorrect : table.partialFold admit Value.node everything ⟨2, by decide⟩ = some (interpret table ⟨2, by decide⟩) := by rfl
