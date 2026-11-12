import GraphSelectionExamples
open FormalGraphTable FormalGraphTable.SelectionExamples
def missing : Fin 3 → Bool := fun index => index.val == 2
theorem incorrect : table.Ready admit Value.scalar missing := by
  simp [table, Table.Ready, Row.Ready, missing, admit, known, Fin.last]
