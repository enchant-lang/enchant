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
def row0 : Row 0 := Row.scalar (Scalar.keyword [110, 111])
def table1 : Table 1 := .push table0 row0
def counts1 : Fin 1 → Nat := extend counts0 1
theorem counts1_eq : Table.fold (fun _ => 1) nodeCountAlgebra table1 = counts1 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table0 row0 counts0 1 counts0_eq (by decide +kernel)
def heights1 : Fin 1 → Nat := extend heights0 0
theorem heights1_eq : Table.fold (fun _ => 0) heightAlgebra table1 = heights1 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table0 row0 heights0 0 heights0_eq (by decide +kernel)
def row1 : Row 1 := Row.scalar (Scalar.keyword [121, 101, 115])
def table2 : Table 2 := .push table1 row1
def counts2 : Fin 2 → Nat := extend counts1 1
theorem counts2_eq : Table.fold (fun _ => 1) nodeCountAlgebra table2 = counts2 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table1 row1 counts1 1 counts1_eq (by decide +kernel)
def heights2 : Fin 2 → Nat := extend heights1 0
theorem heights2_eq : Table.fold (fun _ => 0) heightAlgebra table2 = heights2 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table1 row1 heights1 0 heights1_eq (by decide +kernel)
def row2 : Row 2 := Row.scalar (Scalar.float64 ⟨9223372036854775808, by decide⟩)
def table3 : Table 3 := .push table2 row2
def counts3 : Fin 3 → Nat := extend counts2 1
theorem counts3_eq : Table.fold (fun _ => 1) nodeCountAlgebra table3 = counts3 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table2 row2 counts2 1 counts2_eq (by decide +kernel)
def heights3 : Fin 3 → Nat := extend heights2 0
theorem heights3_eq : Table.fold (fun _ => 0) heightAlgebra table3 = heights3 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table2 row2 heights2 0 heights2_eq (by decide +kernel)
def row3 : Row 3 := Row.scalar (Scalar.boolean false)
def table4 : Table 4 := .push table3 row3
def counts4 : Fin 4 → Nat := extend counts3 1
theorem counts4_eq : Table.fold (fun _ => 1) nodeCountAlgebra table4 = counts4 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table3 row3 counts3 1 counts3_eq (by decide +kernel)
def heights4 : Fin 4 → Nat := extend heights3 0
theorem heights4_eq : Table.fold (fun _ => 0) heightAlgebra table4 = heights4 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table3 row3 heights3 0 heights3_eq (by decide +kernel)
def row4 : Row 4 := Row.scalar (Scalar.keyword [102, 108, 111, 97, 116, 105, 110, 103])
def table5 : Table 5 := .push table4 row4
def counts5 : Fin 5 → Nat := extend counts4 1
theorem counts5_eq : Table.fold (fun _ => 1) nodeCountAlgebra table5 = counts5 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table4 row4 counts4 1 counts4_eq (by decide +kernel)
def heights5 : Fin 5 → Nat := extend heights4 0
theorem heights5_eq : Table.fold (fun _ => 0) heightAlgebra table5 = heights5 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table4 row4 heights4 0 heights4_eq (by decide +kernel)
def row5 : Row 5 := Row.scalar (Scalar.keyword [112, 111, 115, 105, 116, 105, 118, 101, 45, 122, 101, 114, 111])
def table6 : Table 6 := .push table5 row5
def counts6 : Fin 6 → Nat := extend counts5 1
theorem counts6_eq : Table.fold (fun _ => 1) nodeCountAlgebra table6 = counts6 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table5 row5 counts5 1 counts5_eq (by decide +kernel)
def heights6 : Fin 6 → Nat := extend heights5 0
theorem heights6_eq : Table.fold (fun _ => 0) heightAlgebra table6 = heights6 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table5 row5 heights5 0 heights5_eq (by decide +kernel)
def row6 : Row 6 := Row.scalar (Scalar.integer (0))
def table7 : Table 7 := .push table6 row6
def counts7 : Fin 7 → Nat := extend counts6 1
theorem counts7_eq : Table.fold (fun _ => 1) nodeCountAlgebra table7 = counts7 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table6 row6 counts6 1 counts6_eq (by decide +kernel)
def heights7 : Fin 7 → Nat := extend heights6 0
theorem heights7_eq : Table.fold (fun _ => 0) heightAlgebra table7 = heights7 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table6 row6 heights6 0 heights6_eq (by decide +kernel)
def row7 : Row 7 := Row.scalar (Scalar.integer (1))
def table8 : Table 8 := .push table7 row7
def counts8 : Fin 8 → Nat := extend counts7 1
theorem counts8_eq : Table.fold (fun _ => 1) nodeCountAlgebra table8 = counts8 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table7 row7 counts7 1 counts7_eq (by decide +kernel)
def heights8 : Fin 8 → Nat := extend heights7 0
theorem heights8_eq : Table.fold (fun _ => 0) heightAlgebra table8 = heights8 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table7 row7 heights7 0 heights7_eq (by decide +kernel)
def row8 : Row 8 := Row.scalar (Scalar.symbol [109, 111, 100, 101, 108, 47, 110, 97, 109, 101])
def table9 : Table 9 := .push table8 row8
def counts9 : Fin 9 → Nat := extend counts8 1
theorem counts9_eq : Table.fold (fun _ => 1) nodeCountAlgebra table9 = counts9 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table8 row8 counts8 1 counts8_eq (by decide +kernel)
def heights9 : Fin 9 → Nat := extend heights8 0
theorem heights9_eq : Table.fold (fun _ => 0) heightAlgebra table9 = heights9 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table8 row8 heights8 0 heights8_eq (by decide +kernel)
def row9 : Row 9 := Row.scalar (Scalar.boolean true)
def table10 : Table 10 := .push table9 row9
def counts10 : Fin 10 → Nat := extend counts9 1
theorem counts10_eq : Table.fold (fun _ => 1) nodeCountAlgebra table10 = counts10 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table9 row9 counts9 1 counts9_eq (by decide +kernel)
def heights10 : Fin 10 → Nat := extend heights9 0
theorem heights10_eq : Table.fold (fun _ => 0) heightAlgebra table10 = heights10 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table9 row9 heights9 0 heights9_eq (by decide +kernel)
def row10 : Row 10 := Row.scalar (Scalar.integer (-3))
def table11 : Table 11 := .push table10 row10
def counts11 : Fin 11 → Nat := extend counts10 1
theorem counts11_eq : Table.fold (fun _ => 1) nodeCountAlgebra table11 = counts11 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table10 row10 counts10 1 counts10_eq (by decide +kernel)
def heights11 : Fin 11 → Nat := extend heights10 0
theorem heights11_eq : Table.fold (fun _ => 0) heightAlgebra table11 = heights11 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table10 row10 heights10 0 heights10_eq (by decide +kernel)
def row11 : Row 11 := Row.scalar (Scalar.bytes [0, 255, 128])
def table12 : Table 12 := .push table11 row11
def counts12 : Fin 12 → Nat := extend counts11 1
theorem counts12_eq : Table.fold (fun _ => 1) nodeCountAlgebra table12 = counts12 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table11 row11 counts11 1 counts11_eq (by decide +kernel)
def heights12 : Fin 12 → Nat := extend heights11 0
theorem heights12_eq : Table.fold (fun _ => 0) heightAlgebra table12 = heights12 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table11 row11 heights11 0 heights11_eq (by decide +kernel)
def row12 : Row 12 := Row.scalar (Scalar.keyword [110, 101, 103, 97, 116, 105, 118, 101, 45, 122, 101, 114, 111])
def table13 : Table 13 := .push table12 row12
def counts13 : Fin 13 → Nat := extend counts12 1
theorem counts13_eq : Table.fold (fun _ => 1) nodeCountAlgebra table13 = counts13 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table12 row12 counts12 1 counts12_eq (by decide +kernel)
def heights13 : Fin 13 → Nat := extend heights12 0
theorem heights13_eq : Table.fold (fun _ => 0) heightAlgebra table13 = heights13 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table12 row12 heights12 0 heights12_eq (by decide +kernel)
def row13 : Row 13 := Row.scalar (Scalar.keyword [105, 110, 116, 101, 103, 101, 114])
def table14 : Table 14 := .push table13 row13
def counts14 : Fin 14 → Nat := extend counts13 1
theorem counts14_eq : Table.fold (fun _ => 1) nodeCountAlgebra table14 = counts14 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table13 row13 counts13 1 counts13_eq (by decide +kernel)
def heights14 : Fin 14 → Nat := extend heights13 0
theorem heights14_eq : Table.fold (fun _ => 0) heightAlgebra table14 = heights14 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table13 row13 heights13 0 heights13_eq (by decide +kernel)
def row14 : Row 14 := Row.scalar (Scalar.float64 ⟨0, by decide⟩)
def table15 : Table 15 := .push table14 row14
def counts15 : Fin 15 → Nat := extend counts14 1
theorem counts15_eq : Table.fold (fun _ => 1) nodeCountAlgebra table15 = counts15 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table14 row14 counts14 1 counts14_eq (by decide +kernel)
def heights15 : Fin 15 → Nat := extend heights14 0
theorem heights15_eq : Table.fold (fun _ => 0) heightAlgebra table15 = heights15 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table14 row14 heights14 0 heights14_eq (by decide +kernel)
def row15 : Row 15 := Row.scalar (Scalar.nil)
def table16 : Table 16 := .push table15 row15
def counts16 : Fin 16 → Nat := extend counts15 1
theorem counts16_eq : Table.fold (fun _ => 1) nodeCountAlgebra table16 = counts16 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table15 row15 counts15 1 counts15_eq (by decide +kernel)
def heights16 : Fin 16 → Nat := extend heights15 0
theorem heights16_eq : Table.fold (fun _ => 0) heightAlgebra table16 = heights16 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table15 row15 heights15 0 heights15_eq (by decide +kernel)
def row16 : Row 16 := Row.scalar (Scalar.float64 ⟨4607182418800017408, by decide⟩)
def table17 : Table 17 := .push table16 row16
def counts17 : Fin 17 → Nat := extend counts16 1
theorem counts17_eq : Table.fold (fun _ => 1) nodeCountAlgebra table17 = counts17 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table16 row16 counts16 1 counts16_eq (by decide +kernel)
def heights17 : Fin 17 → Nat := extend heights16 0
theorem heights17_eq : Table.fold (fun _ => 0) heightAlgebra table17 = heights17 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table16 row16 heights16 0 heights16_eq (by decide +kernel)
def row17 : Row 17 := Row.scalar (Scalar.keyword [111, 107])
def table18 : Table 18 := .push table17 row17
def counts18 : Fin 18 → Nat := extend counts17 1
theorem counts18_eq : Table.fold (fun _ => 1) nodeCountAlgebra table18 = counts18 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table17 row17 counts17 1 counts17_eq (by decide +kernel)
def heights18 : Fin 18 → Nat := extend heights17 0
theorem heights18_eq : Table.fold (fun _ => 0) heightAlgebra table18 = heights18 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table17 row17 heights17 0 heights17_eq (by decide +kernel)
def row18 : Row 18 := Row.scalar (Scalar.keyword [114, 101, 97, 100, 121])
def table19 : Table 19 := .push table18 row18
def counts19 : Fin 19 → Nat := extend counts18 1
theorem counts19_eq : Table.fold (fun _ => 1) nodeCountAlgebra table19 = counts19 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table18 row18 counts18 1 counts18_eq (by decide +kernel)
def heights19 : Fin 19 → Nat := extend heights18 0
theorem heights19_eq : Table.fold (fun _ => 0) heightAlgebra table19 = heights19 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table18 row18 heights18 0 heights18_eq (by decide +kernel)
def row19 : Row 19 := Row.node (Kind.map 4) (fun (slot : Fin 4 × Bool) => if slot.2 then (List.get ([⟨12, by decide⟩, ⟨13, by decide⟩, ⟨5, by decide⟩, ⟨4, by decide⟩] : List (Fin 19))) slot.1 else (List.get ([⟨2, by decide⟩, ⟨7, by decide⟩, ⟨14, by decide⟩, ⟨16, by decide⟩] : List (Fin 19))) slot.1)
def table20 : Table 20 := .push table19 row19
def counts20 : Fin 20 → Nat := extend counts19 9
theorem counts20_eq : Table.fold (fun _ => 1) nodeCountAlgebra table20 = counts20 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table19 row19 counts19 9 counts19_eq (by decide +kernel)
def heights20 : Fin 20 → Nat := extend heights19 1
theorem heights20_eq : Table.fold (fun _ => 0) heightAlgebra table20 = heights20 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table19 row19 heights19 1 heights19_eq (by decide +kernel)
def row20 : Row 20 := Row.node (Kind.list 2) (List.get ([⟨7, by decide⟩, ⟨15, by decide⟩] : List (Fin 20)))
def table21 : Table 21 := .push table20 row20
def counts21 : Fin 21 → Nat := extend counts20 3
theorem counts21_eq : Table.fold (fun _ => 1) nodeCountAlgebra table21 = counts21 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table20 row20 counts20 3 counts20_eq (by decide +kernel)
def heights21 : Fin 21 → Nat := extend heights20 1
theorem heights21_eq : Table.fold (fun _ => 0) heightAlgebra table21 = heights21 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table20 row20 heights20 1 heights20_eq (by decide +kernel)
def row21 : Row 21 := Row.node (Kind.set 2) (List.get ([⟨0, by decide⟩, ⟨1, by decide⟩] : List (Fin 21)))
def table22 : Table 22 := .push table21 row21
def counts22 : Fin 22 → Nat := extend counts21 3
theorem counts22_eq : Table.fold (fun _ => 1) nodeCountAlgebra table22 = counts22 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table21 row21 counts21 3 counts21_eq (by decide +kernel)
def heights22 : Fin 22 → Nat := extend heights21 1
theorem heights22_eq : Table.fold (fun _ => 0) heightAlgebra table22 = heights22 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table21 row21 heights21 1 heights21_eq (by decide +kernel)
def row22 : Row 22 := Row.node (Kind.tuple 2) (List.get ([⟨17, by decide⟩, ⟨7, by decide⟩] : List (Fin 22)))
def table23 : Table 23 := .push table22 row22
def counts23 : Fin 23 → Nat := extend counts22 3
theorem counts23_eq : Table.fold (fun _ => 1) nodeCountAlgebra table23 = counts23 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table22 row22 counts22 3 counts22_eq (by decide +kernel)
def heights23 : Fin 23 → Nat := extend heights22 1
theorem heights23_eq : Table.fold (fun _ => 0) heightAlgebra table23 = heights23 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table22 row22 heights22 1 heights22_eq (by decide +kernel)
def row23 : Row 23 := Row.node (Kind.vector 16) (List.get ([⟨15, by decide⟩, ⟨9, by decide⟩, ⟨3, by decide⟩, ⟨10, by decide⟩, ⟨6, by decide⟩, ⟨7, by decide⟩, ⟨16, by decide⟩, ⟨14, by decide⟩, ⟨2, by decide⟩, ⟨11, by decide⟩, ⟨18, by decide⟩, ⟨8, by decide⟩, ⟨20, by decide⟩, ⟨21, by decide⟩, ⟨22, by decide⟩, ⟨19, by decide⟩] : List (Fin 23)))
def table24 : Table 24 := .push table23 row23
def counts24 : Fin 24 → Nat := extend counts23 31
theorem counts24_eq : Table.fold (fun _ => 1) nodeCountAlgebra table24 = counts24 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table23 row23 counts23 31 counts23_eq (by decide +kernel)
def heights24 : Fin 24 → Nat := extend heights23 2
theorem heights24_eq : Table.fold (fun _ => 0) heightAlgebra table24 = heights24 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table23 row23 heights23 2 heights23_eq (by decide +kernel)
theorem original_expanded_nodes : (interpret table24 ⟨23, by decide⟩).expandedNodes = 31 := by
  exact (expanded_node_count_agrees table24 ⟨23, by decide⟩).trans ((congrFun counts24_eq ⟨23, by decide⟩).trans (by decide +kernel))
theorem original_depth : (interpret table24 ⟨23, by decide⟩).height = 2 := by
  exact (height_agrees table24 ⟨23, by decide⟩).trans ((congrFun heights24_eq ⟨23, by decide⟩).trans (by decide +kernel))
#print axioms original_expanded_nodes
#print axioms original_depth
end GraphInstance
