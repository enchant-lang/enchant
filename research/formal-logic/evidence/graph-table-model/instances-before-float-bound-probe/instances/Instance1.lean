import GraphTable
set_option autoImplicit false
set_option maxRecDepth 100000
set_option maxHeartbeats 8000000
open FormalGraphTable
namespace GraphInstance
def table0 : Table 0 := .empty
def table1 : Table 1 := .push table0 (Row.scalar (Scalar.keyword [103, 114, 97, 112, 104, 46, 109, 111, 100, 101, 108, 46, 117, 110, 102, 97, 109, 105, 108, 105, 97, 114, 46, 52, 53]))
def table2 : Table 2 := .push table1 (Row.node (Kind.vector 2) (Fin.cases ⟨0, by decide⟩ (Fin.cases ⟨0, by decide⟩ (fun i => Fin.elim0 i))))
def table3 : Table 3 := .push table2 (Row.node (Kind.vector 2) (Fin.cases ⟨1, by decide⟩ (Fin.cases ⟨1, by decide⟩ (fun i => Fin.elim0 i))))
def table4 : Table 4 := .push table3 (Row.node (Kind.vector 2) (Fin.cases ⟨2, by decide⟩ (Fin.cases ⟨2, by decide⟩ (fun i => Fin.elim0 i))))
def table5 : Table 5 := .push table4 (Row.node (Kind.vector 2) (Fin.cases ⟨3, by decide⟩ (Fin.cases ⟨3, by decide⟩ (fun i => Fin.elim0 i))))
def table6 : Table 6 := .push table5 (Row.node (Kind.vector 2) (Fin.cases ⟨4, by decide⟩ (Fin.cases ⟨4, by decide⟩ (fun i => Fin.elim0 i))))
def table7 : Table 7 := .push table6 (Row.node (Kind.vector 2) (Fin.cases ⟨5, by decide⟩ (Fin.cases ⟨5, by decide⟩ (fun i => Fin.elim0 i))))
def table8 : Table 8 := .push table7 (Row.node (Kind.vector 2) (Fin.cases ⟨6, by decide⟩ (Fin.cases ⟨6, by decide⟩ (fun i => Fin.elim0 i))))
def table9 : Table 9 := .push table8 (Row.node (Kind.vector 2) (Fin.cases ⟨7, by decide⟩ (Fin.cases ⟨7, by decide⟩ (fun i => Fin.elim0 i))))
def table10 : Table 10 := .push table9 (Row.node (Kind.vector 2) (Fin.cases ⟨8, by decide⟩ (Fin.cases ⟨8, by decide⟩ (fun i => Fin.elim0 i))))
def table11 : Table 11 := .push table10 (Row.node (Kind.vector 2) (Fin.cases ⟨9, by decide⟩ (Fin.cases ⟨9, by decide⟩ (fun i => Fin.elim0 i))))
def table12 : Table 12 := .push table11 (Row.node (Kind.vector 2) (Fin.cases ⟨10, by decide⟩ (Fin.cases ⟨10, by decide⟩ (fun i => Fin.elim0 i))))
def table13 : Table 13 := .push table12 (Row.node (Kind.vector 2) (Fin.cases ⟨11, by decide⟩ (Fin.cases ⟨11, by decide⟩ (fun i => Fin.elim0 i))))
def table14 : Table 14 := .push table13 (Row.node (Kind.vector 2) (Fin.cases ⟨12, by decide⟩ (Fin.cases ⟨12, by decide⟩ (fun i => Fin.elim0 i))))
def table15 : Table 15 := .push table14 (Row.node (Kind.vector 2) (Fin.cases ⟨13, by decide⟩ (Fin.cases ⟨13, by decide⟩ (fun i => Fin.elim0 i))))
def table16 : Table 16 := .push table15 (Row.node (Kind.vector 2) (Fin.cases ⟨14, by decide⟩ (Fin.cases ⟨14, by decide⟩ (fun i => Fin.elim0 i))))
def table17 : Table 17 := .push table16 (Row.node (Kind.vector 2) (Fin.cases ⟨15, by decide⟩ (Fin.cases ⟨15, by decide⟩ (fun i => Fin.elim0 i))))
theorem original_expanded_nodes : (interpret table17 ⟨16, by decide⟩).expandedNodes = 131071 := by
  rw [expanded_node_count_agrees]
  decide
theorem original_depth : (interpret table17 ⟨16, by decide⟩).height = 16 := by
  rw [height_agrees]
  decide
#print axioms original_expanded_nodes
#print axioms original_depth
end GraphInstance
