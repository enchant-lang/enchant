import GraphSelectionExamples
open FormalGraphTable FormalGraphTable.SelectionExamples
theorem incorrect : table.partialFold admit Value.node selected ⟨0, by decide⟩ = some (.scalar (.integer 8)) := by rfl
