import GraphTable
set_option autoImplicit false
set_option maxRecDepth 100000
set_option maxHeartbeats 8000000
open FormalGraphTable
namespace GraphInstance
def table0 : Table 0 := .empty
def counts0 : Fin 0 → Nat := fun i => Fin.elim0 i
def heights0 : Fin 0 → Nat := fun i => Fin.elim0 i
theorem counts0_eq : Table.fold (fun _ => 1) nodeCountAlgebra table0 = counts0 := rfl
theorem heights0_eq : Table.fold (fun _ => 0) heightAlgebra table0 = heights0 := rfl
def row0 : Row 0 := Row.scalar (Scalar.keyword [103, 114, 97, 112, 104, 46, 109, 111, 100, 101, 108, 46, 117, 110, 102, 97, 109, 105, 108, 105, 97, 114, 46, 52, 53])
def table1 : Table 1 := .push table0 row0
def counts1 : Fin 1 → Nat := extend counts0 1
theorem counts1_eq : Table.fold (fun _ => 1) nodeCountAlgebra table1 = counts1 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table0 row0 counts0 1 counts0_eq (by decide +kernel)
def heights1 : Fin 1 → Nat := extend heights0 0
theorem heights1_eq : Table.fold (fun _ => 0) heightAlgebra table1 = heights1 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table0 row0 heights0 0 heights0_eq (by decide +kernel)
def row1 : Row 1 := Row.node (Kind.vector 2) (List.get ([⟨0, by decide⟩, ⟨0, by decide⟩] : List (Fin 1)))
def table2 : Table 2 := .push table1 row1
def counts2 : Fin 2 → Nat := extend counts1 3
theorem counts2_eq : Table.fold (fun _ => 1) nodeCountAlgebra table2 = counts2 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table1 row1 counts1 3 counts1_eq (by decide +kernel)
def heights2 : Fin 2 → Nat := extend heights1 1
theorem heights2_eq : Table.fold (fun _ => 0) heightAlgebra table2 = heights2 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table1 row1 heights1 1 heights1_eq (by decide +kernel)
def row2 : Row 2 := Row.node (Kind.vector 2) (List.get ([⟨1, by decide⟩, ⟨1, by decide⟩] : List (Fin 2)))
def table3 : Table 3 := .push table2 row2
def counts3 : Fin 3 → Nat := extend counts2 7
theorem counts3_eq : Table.fold (fun _ => 1) nodeCountAlgebra table3 = counts3 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table2 row2 counts2 7 counts2_eq (by decide +kernel)
def heights3 : Fin 3 → Nat := extend heights2 2
theorem heights3_eq : Table.fold (fun _ => 0) heightAlgebra table3 = heights3 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table2 row2 heights2 2 heights2_eq (by decide +kernel)
def row3 : Row 3 := Row.node (Kind.vector 2) (List.get ([⟨2, by decide⟩, ⟨2, by decide⟩] : List (Fin 3)))
def table4 : Table 4 := .push table3 row3
def counts4 : Fin 4 → Nat := extend counts3 15
theorem counts4_eq : Table.fold (fun _ => 1) nodeCountAlgebra table4 = counts4 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table3 row3 counts3 15 counts3_eq (by decide +kernel)
def heights4 : Fin 4 → Nat := extend heights3 3
theorem heights4_eq : Table.fold (fun _ => 0) heightAlgebra table4 = heights4 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table3 row3 heights3 3 heights3_eq (by decide +kernel)
def row4 : Row 4 := Row.node (Kind.vector 2) (List.get ([⟨3, by decide⟩, ⟨3, by decide⟩] : List (Fin 4)))
def table5 : Table 5 := .push table4 row4
def counts5 : Fin 5 → Nat := extend counts4 31
theorem counts5_eq : Table.fold (fun _ => 1) nodeCountAlgebra table5 = counts5 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table4 row4 counts4 31 counts4_eq (by decide +kernel)
def heights5 : Fin 5 → Nat := extend heights4 4
theorem heights5_eq : Table.fold (fun _ => 0) heightAlgebra table5 = heights5 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table4 row4 heights4 4 heights4_eq (by decide +kernel)
def row5 : Row 5 := Row.node (Kind.vector 2) (List.get ([⟨4, by decide⟩, ⟨4, by decide⟩] : List (Fin 5)))
def table6 : Table 6 := .push table5 row5
def counts6 : Fin 6 → Nat := extend counts5 63
theorem counts6_eq : Table.fold (fun _ => 1) nodeCountAlgebra table6 = counts6 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table5 row5 counts5 63 counts5_eq (by decide +kernel)
def heights6 : Fin 6 → Nat := extend heights5 5
theorem heights6_eq : Table.fold (fun _ => 0) heightAlgebra table6 = heights6 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table5 row5 heights5 5 heights5_eq (by decide +kernel)
def row6 : Row 6 := Row.node (Kind.vector 2) (List.get ([⟨5, by decide⟩, ⟨5, by decide⟩] : List (Fin 6)))
def table7 : Table 7 := .push table6 row6
def counts7 : Fin 7 → Nat := extend counts6 127
theorem counts7_eq : Table.fold (fun _ => 1) nodeCountAlgebra table7 = counts7 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table6 row6 counts6 127 counts6_eq (by decide +kernel)
def heights7 : Fin 7 → Nat := extend heights6 6
theorem heights7_eq : Table.fold (fun _ => 0) heightAlgebra table7 = heights7 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table6 row6 heights6 6 heights6_eq (by decide +kernel)
def row7 : Row 7 := Row.node (Kind.vector 2) (List.get ([⟨6, by decide⟩, ⟨6, by decide⟩] : List (Fin 7)))
def table8 : Table 8 := .push table7 row7
def counts8 : Fin 8 → Nat := extend counts7 255
theorem counts8_eq : Table.fold (fun _ => 1) nodeCountAlgebra table8 = counts8 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table7 row7 counts7 255 counts7_eq (by decide +kernel)
def heights8 : Fin 8 → Nat := extend heights7 7
theorem heights8_eq : Table.fold (fun _ => 0) heightAlgebra table8 = heights8 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table7 row7 heights7 7 heights7_eq (by decide +kernel)
def row8 : Row 8 := Row.node (Kind.vector 2) (List.get ([⟨7, by decide⟩, ⟨7, by decide⟩] : List (Fin 8)))
def table9 : Table 9 := .push table8 row8
def counts9 : Fin 9 → Nat := extend counts8 511
theorem counts9_eq : Table.fold (fun _ => 1) nodeCountAlgebra table9 = counts9 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table8 row8 counts8 511 counts8_eq (by decide +kernel)
def heights9 : Fin 9 → Nat := extend heights8 8
theorem heights9_eq : Table.fold (fun _ => 0) heightAlgebra table9 = heights9 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table8 row8 heights8 8 heights8_eq (by decide +kernel)
def row9 : Row 9 := Row.node (Kind.vector 2) (List.get ([⟨8, by decide⟩, ⟨8, by decide⟩] : List (Fin 9)))
def table10 : Table 10 := .push table9 row9
def counts10 : Fin 10 → Nat := extend counts9 1023
theorem counts10_eq : Table.fold (fun _ => 1) nodeCountAlgebra table10 = counts10 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table9 row9 counts9 1023 counts9_eq (by decide +kernel)
def heights10 : Fin 10 → Nat := extend heights9 9
theorem heights10_eq : Table.fold (fun _ => 0) heightAlgebra table10 = heights10 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table9 row9 heights9 9 heights9_eq (by decide +kernel)
def row10 : Row 10 := Row.node (Kind.vector 2) (List.get ([⟨9, by decide⟩, ⟨9, by decide⟩] : List (Fin 10)))
def table11 : Table 11 := .push table10 row10
def counts11 : Fin 11 → Nat := extend counts10 2047
theorem counts11_eq : Table.fold (fun _ => 1) nodeCountAlgebra table11 = counts11 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table10 row10 counts10 2047 counts10_eq (by decide +kernel)
def heights11 : Fin 11 → Nat := extend heights10 10
theorem heights11_eq : Table.fold (fun _ => 0) heightAlgebra table11 = heights11 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table10 row10 heights10 10 heights10_eq (by decide +kernel)
def row11 : Row 11 := Row.node (Kind.vector 2) (List.get ([⟨10, by decide⟩, ⟨10, by decide⟩] : List (Fin 11)))
def table12 : Table 12 := .push table11 row11
def counts12 : Fin 12 → Nat := extend counts11 4095
theorem counts12_eq : Table.fold (fun _ => 1) nodeCountAlgebra table12 = counts12 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table11 row11 counts11 4095 counts11_eq (by decide +kernel)
def heights12 : Fin 12 → Nat := extend heights11 11
theorem heights12_eq : Table.fold (fun _ => 0) heightAlgebra table12 = heights12 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table11 row11 heights11 11 heights11_eq (by decide +kernel)
def row12 : Row 12 := Row.node (Kind.vector 2) (List.get ([⟨11, by decide⟩, ⟨11, by decide⟩] : List (Fin 12)))
def table13 : Table 13 := .push table12 row12
def counts13 : Fin 13 → Nat := extend counts12 8191
theorem counts13_eq : Table.fold (fun _ => 1) nodeCountAlgebra table13 = counts13 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table12 row12 counts12 8191 counts12_eq (by decide +kernel)
def heights13 : Fin 13 → Nat := extend heights12 12
theorem heights13_eq : Table.fold (fun _ => 0) heightAlgebra table13 = heights13 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table12 row12 heights12 12 heights12_eq (by decide +kernel)
def row13 : Row 13 := Row.node (Kind.vector 2) (List.get ([⟨12, by decide⟩, ⟨12, by decide⟩] : List (Fin 13)))
def table14 : Table 14 := .push table13 row13
def counts14 : Fin 14 → Nat := extend counts13 16383
theorem counts14_eq : Table.fold (fun _ => 1) nodeCountAlgebra table14 = counts14 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table13 row13 counts13 16383 counts13_eq (by decide +kernel)
def heights14 : Fin 14 → Nat := extend heights13 13
theorem heights14_eq : Table.fold (fun _ => 0) heightAlgebra table14 = heights14 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table13 row13 heights13 13 heights13_eq (by decide +kernel)
def row14 : Row 14 := Row.node (Kind.vector 2) (List.get ([⟨13, by decide⟩, ⟨13, by decide⟩] : List (Fin 14)))
def table15 : Table 15 := .push table14 row14
def counts15 : Fin 15 → Nat := extend counts14 32767
theorem counts15_eq : Table.fold (fun _ => 1) nodeCountAlgebra table15 = counts15 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table14 row14 counts14 32767 counts14_eq (by decide +kernel)
def heights15 : Fin 15 → Nat := extend heights14 14
theorem heights15_eq : Table.fold (fun _ => 0) heightAlgebra table15 = heights15 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table14 row14 heights14 14 heights14_eq (by decide +kernel)
def row15 : Row 15 := Row.node (Kind.vector 2) (List.get ([⟨14, by decide⟩, ⟨14, by decide⟩] : List (Fin 15)))
def table16 : Table 16 := .push table15 row15
def counts16 : Fin 16 → Nat := extend counts15 65535
theorem counts16_eq : Table.fold (fun _ => 1) nodeCountAlgebra table16 = counts16 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table15 row15 counts15 65535 counts15_eq (by decide +kernel)
def heights16 : Fin 16 → Nat := extend heights15 15
theorem heights16_eq : Table.fold (fun _ => 0) heightAlgebra table16 = heights16 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table15 row15 heights15 15 heights15_eq (by decide +kernel)
def row16 : Row 16 := Row.node (Kind.vector 2) (List.get ([⟨15, by decide⟩, ⟨15, by decide⟩] : List (Fin 16)))
def table17 : Table 17 := .push table16 row16
def counts17 : Fin 17 → Nat := extend counts16 131071
theorem counts17_eq : Table.fold (fun _ => 1) nodeCountAlgebra table17 = counts17 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table16 row16 counts16 131071 counts16_eq (by decide +kernel)
def heights17 : Fin 17 → Nat := extend heights16 16
theorem heights17_eq : Table.fold (fun _ => 0) heightAlgebra table17 = heights17 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table16 row16 heights16 16 heights16_eq (by decide +kernel)
theorem original_expanded_nodes : (interpret table17 ⟨16, by decide⟩).expandedNodes = 131071 := by
  exact (expanded_node_count_agrees table17 ⟨16, by decide⟩).trans ((congrFun counts17_eq ⟨16, by decide⟩).trans (by decide +kernel))
theorem original_depth : (interpret table17 ⟨16, by decide⟩).height = 16 := by
  exact (height_agrees table17 ⟨16, by decide⟩).trans ((congrFun heights17_eq ⟨16, by decide⟩).trans (by decide +kernel))
#print axioms original_expanded_nodes
#print axioms original_depth
end GraphInstance
