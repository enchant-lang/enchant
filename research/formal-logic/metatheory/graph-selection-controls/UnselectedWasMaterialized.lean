import GraphSelectionExamples
open FormalGraphTable FormalGraphTable.SelectionExamples
theorem incorrect : table.partialFold admit Value.node selected ⟨1, by decide⟩ = some (.scalar unfamiliar) := by rfl
