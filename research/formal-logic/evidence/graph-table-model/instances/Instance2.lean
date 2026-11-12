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
def row0 : Row 0 := Row.scalar (Scalar.bytes [97, 115, 115, 117, 109, 101, 47, 48])
def table1 : Table 1 := .push table0 row0
def counts1 : Fin 1 → Nat := extend counts0 1
theorem counts1_eq : Table.fold (fun _ => 1) nodeCountAlgebra table1 = counts1 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table0 row0 counts0 1 counts0_eq (by decide +kernel)
def heights1 : Fin 1 → Nat := extend heights0 0
theorem heights1_eq : Table.fold (fun _ => 0) heightAlgebra table1 = heights1 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table0 row0 heights0 0 heights0_eq (by decide +kernel)
def row1 : Row 1 := Row.scalar (Scalar.keyword [107, 105, 110, 100])
def table2 : Table 2 := .push table1 row1
def counts2 : Fin 2 → Nat := extend counts1 1
theorem counts2_eq : Table.fold (fun _ => 1) nodeCountAlgebra table2 = counts2 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table1 row1 counts1 1 counts1_eq (by decide +kernel)
def heights2 : Fin 2 → Nat := extend heights1 0
theorem heights2_eq : Table.fold (fun _ => 0) heightAlgebra table2 = heights2 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table1 row1 heights1 0 heights1_eq (by decide +kernel)
def row2 : Row 2 := Row.scalar (Scalar.keyword [118, 97, 108, 117, 101, 115])
def table3 : Table 3 := .push table2 row2
def counts3 : Fin 3 → Nat := extend counts2 1
theorem counts3_eq : Table.fold (fun _ => 1) nodeCountAlgebra table3 = counts3 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table2 row2 counts2 1 counts2_eq (by decide +kernel)
def heights3 : Fin 3 → Nat := extend heights2 0
theorem heights3_eq : Table.fold (fun _ => 0) heightAlgebra table3 = heights3 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table2 row2 heights2 0 heights2_eq (by decide +kernel)
def row3 : Row 3 := Row.scalar (Scalar.keyword [102, 111, 114, 109, 97, 108, 47, 115, 99, 97, 108, 97, 114, 45, 118, 49])
def table4 : Table 4 := .push table3 row3
def counts4 : Fin 4 → Nat := extend counts3 1
theorem counts4_eq : Table.fold (fun _ => 1) nodeCountAlgebra table4 = counts4 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table3 row3 counts3 1 counts3_eq (by decide +kernel)
def heights4 : Fin 4 → Nat := extend heights3 0
theorem heights4_eq : Table.fold (fun _ => 0) heightAlgebra table4 = heights4 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table3 row3 heights3 0 heights3_eq (by decide +kernel)
def row4 : Row 4 := Row.scalar (Scalar.keyword [118, 97, 114])
def table5 : Table 5 := .push table4 row4
def counts5 : Fin 5 → Nat := extend counts4 1
theorem counts5_eq : Table.fold (fun _ => 1) nodeCountAlgebra table5 = counts5 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table4 row4 counts4 1 counts4_eq (by decide +kernel)
def heights5 : Fin 5 → Nat := extend heights4 0
theorem heights5_eq : Table.fold (fun _ => 0) heightAlgebra table5 = heights5 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table4 row4 heights4 0 heights4_eq (by decide +kernel)
def row5 : Row 5 := Row.scalar (Scalar.keyword [118, 97, 108, 117, 101])
def table6 : Table 6 := .push table5 row5
def counts6 : Fin 6 → Nat := extend counts5 1
theorem counts6_eq : Table.fold (fun _ => 1) nodeCountAlgebra table6 = counts6 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table5 row5 counts5 1 counts5_eq (by decide +kernel)
def heights6 : Fin 6 → Nat := extend heights5 0
theorem heights6_eq : Table.fold (fun _ => 0) heightAlgebra table6 = heights6 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table5 row5 heights5 0 heights5_eq (by decide +kernel)
def row6 : Row 6 := Row.scalar (Scalar.keyword [116, 101, 114, 109])
def table7 : Table 7 := .push table6 row6
def counts7 : Fin 7 → Nat := extend counts6 1
theorem counts7_eq : Table.fold (fun _ => 1) nodeCountAlgebra table7 = counts7 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table6 row6 counts6 1 counts6_eq (by decide +kernel)
def heights7 : Fin 7 → Nat := extend heights6 0
theorem heights7_eq : Table.fold (fun _ => 0) heightAlgebra table7 = heights7 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table6 row6 heights6 0 heights6_eq (by decide +kernel)
def row7 : Row 7 := Row.scalar (Scalar.keyword [101, 114, 114, 111, 114, 115])
def table8 : Table 8 := .push table7 row7
def counts8 : Fin 8 → Nat := extend counts7 1
theorem counts8_eq : Table.fold (fun _ => 1) nodeCountAlgebra table8 = counts8 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table7 row7 counts7 1 counts7_eq (by decide +kernel)
def heights8 : Fin 8 → Nat := extend heights7 0
theorem heights8_eq : Table.fold (fun _ => 0) heightAlgebra table8 = heights8 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table7 row7 heights7 0 heights7_eq (by decide +kernel)
def row8 : Row 8 := Row.scalar (Scalar.keyword [101, 110, 99, 104, 97, 110, 116, 47, 102, 111, 114, 109, 97, 108, 45, 112, 114, 101, 118, 105, 101, 119, 45, 118, 49])
def table9 : Table 9 := .push table8 row8
def counts9 : Fin 9 → Nat := extend counts8 1
theorem counts9_eq : Table.fold (fun _ => 1) nodeCountAlgebra table9 = counts9 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table8 row8 counts8 1 counts8_eq (by decide +kernel)
def heights9 : Fin 9 → Nat := extend heights8 0
theorem heights9_eq : Table.fold (fun _ => 0) heightAlgebra table9 = heights9 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table8 row8 heights8 0 heights8_eq (by decide +kernel)
def row9 : Row 9 := Row.scalar (Scalar.keyword [102, 111, 114, 109, 97, 108, 47, 116, 101, 114, 109])
def table10 : Table 10 := .push table9 row9
def counts10 : Fin 10 → Nat := extend counts9 1
theorem counts10_eq : Table.fold (fun _ => 1) nodeCountAlgebra table10 = counts10 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table9 row9 counts9 1 counts9_eq (by decide +kernel)
def heights10 : Fin 10 → Nat := extend heights9 0
theorem heights10_eq : Table.fold (fun _ => 0) heightAlgebra table10 = heights10 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table9 row9 heights9 0 heights9_eq (by decide +kernel)
def row10 : Row 10 := Row.scalar (Scalar.keyword [112, 114, 111, 102, 105, 108, 101, 115])
def table11 : Table 11 := .push table10 row10
def counts11 : Fin 11 → Nat := extend counts10 1
theorem counts11_eq : Table.fold (fun _ => 1) nodeCountAlgebra table11 = counts11 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table10 row10 counts10 1 counts10_eq (by decide +kernel)
def heights11 : Fin 11 → Nat := extend heights10 0
theorem heights11_eq : Table.fold (fun _ => 0) heightAlgebra table11 = heights11 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table10 row10 heights10 0 heights10_eq (by decide +kernel)
def row11 : Row 11 := Row.scalar (Scalar.keyword [111, 114, 105, 103, 105, 110])
def table12 : Table 12 := .push table11 row11
def counts12 : Fin 12 → Nat := extend counts11 1
theorem counts12_eq : Table.fold (fun _ => 1) nodeCountAlgebra table12 = counts12 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table11 row11 counts11 1 counts11_eq (by decide +kernel)
def heights12 : Fin 12 → Nat := extend heights11 0
theorem heights12_eq : Table.fold (fun _ => 0) heightAlgebra table12 = heights12 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table11 row11 heights11 0 heights11_eq (by decide +kernel)
def row12 : Row 12 := Row.scalar (Scalar.keyword [98, 111, 111, 108])
def table13 : Table 13 := .push table12 row12
def counts13 : Fin 13 → Nat := extend counts12 1
theorem counts13_eq : Table.fold (fun _ => 1) nodeCountAlgebra table13 = counts13 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table12 row12 counts12 1 counts12_eq (by decide +kernel)
def heights13 : Fin 13 → Nat := extend heights12 0
theorem heights13_eq : Table.fold (fun _ => 0) heightAlgebra table13 = heights13 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table12 row12 heights12 0 heights12_eq (by decide +kernel)
def row13 : Row 13 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 49, 46, 50])
def table14 : Table 14 := .push table13 row13
def counts14 : Fin 14 → Nat := extend counts13 1
theorem counts14_eq : Table.fold (fun _ => 1) nodeCountAlgebra table14 = counts14 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table13 row13 counts13 1 counts13_eq (by decide +kernel)
def heights14 : Fin 14 → Nat := extend heights13 0
theorem heights14_eq : Table.fold (fun _ => 0) heightAlgebra table14 = heights14 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table13 row13 heights13 0 heights13_eq (by decide +kernel)
def row14 : Row 14 := Row.scalar (Scalar.integer (1))
def table15 : Table 15 := .push table14 row14
def counts15 : Fin 15 → Nat := extend counts14 1
theorem counts15_eq : Table.fold (fun _ => 1) nodeCountAlgebra table15 = counts15 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table14 row14 counts14 1 counts14_eq (by decide +kernel)
def heights15 : Fin 15 → Nat := extend heights14 0
theorem heights15_eq : Table.fold (fun _ => 0) heightAlgebra table15 = heights15 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table14 row14 heights14 0 heights14_eq (by decide +kernel)
def row15 : Row 15 := Row.scalar (Scalar.keyword [108, 97, 98, 101, 108])
def table16 : Table 16 := .push table15 row15
def counts16 : Fin 16 → Nat := extend counts15 1
theorem counts16_eq : Table.fold (fun _ => 1) nodeCountAlgebra table16 = counts16 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table15 row15 counts15 1 counts15_eq (by decide +kernel)
def heights16 : Fin 16 → Nat := extend heights15 0
theorem heights16_eq : Table.fold (fun _ => 0) heightAlgebra table16 = heights16 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table15 row15 heights15 0 heights15_eq (by decide +kernel)
def row16 : Row 16 := Row.scalar (Scalar.bytes [99, 108, 111, 115, 117, 114, 101])
def table17 : Table 17 := .push table16 row16
def counts17 : Fin 17 → Nat := extend counts16 1
theorem counts17_eq : Table.fold (fun _ => 1) nodeCountAlgebra table17 = counts17 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table16 row16 counts16 1 counts16_eq (by decide +kernel)
def heights17 : Fin 17 → Nat := extend heights16 0
theorem heights17_eq : Table.fold (fun _ => 0) heightAlgebra table17 = heights17 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table16 row16 heights16 0 heights16_eq (by decide +kernel)
def row17 : Row 17 := Row.scalar (Scalar.keyword [110, 111, 116])
def table18 : Table 18 := .push table17 row17
def counts18 : Fin 18 → Nat := extend counts17 1
theorem counts18_eq : Table.fold (fun _ => 1) nodeCountAlgebra table18 = counts18 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table17 row17 counts17 1 counts17_eq (by decide +kernel)
def heights18 : Fin 18 → Nat := extend heights17 0
theorem heights18_eq : Table.fold (fun _ => 0) heightAlgebra table18 = heights18 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table17 row17 heights17 0 heights17_eq (by decide +kernel)
def row18 : Row 18 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 50, 46, 48])
def table19 : Table 19 := .push table18 row18
def counts19 : Fin 19 → Nat := extend counts18 1
theorem counts19_eq : Table.fold (fun _ => 1) nodeCountAlgebra table19 = counts19 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table18 row18 counts18 1 counts18_eq (by decide +kernel)
def heights19 : Fin 19 → Nat := extend heights18 0
theorem heights19_eq : Table.fold (fun _ => 0) heightAlgebra table19 = heights19 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table18 row18 heights18 0 heights18_eq (by decide +kernel)
def row19 : Row 19 := Row.scalar (Scalar.keyword [105, 100])
def table20 : Table 20 := .push table19 row19
def counts20 : Fin 20 → Nat := extend counts19 1
theorem counts20_eq : Table.fold (fun _ => 1) nodeCountAlgebra table20 = counts20 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table19 row19 counts19 1 counts19_eq (by decide +kernel)
def heights20 : Fin 20 → Nat := extend heights19 0
theorem heights20_eq : Table.fold (fun _ => 0) heightAlgebra table20 = heights20 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table19 row19 heights19 0 heights19_eq (by decide +kernel)
def row20 : Row 20 := Row.scalar (Scalar.keyword [102, 105, 110, 105, 116, 101, 45, 114, 101, 108, 97, 116, 105, 111, 110])
def table21 : Table 21 := .push table20 row20
def counts21 : Fin 21 → Nat := extend counts20 1
theorem counts21_eq : Table.fold (fun _ => 1) nodeCountAlgebra table21 = counts21 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table20 row20 counts20 1 counts20_eq (by decide +kernel)
def heights21 : Fin 21 → Nat := extend heights20 0
theorem heights21_eq : Table.fold (fun _ => 0) heightAlgebra table21 = heights21 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table20 row20 heights20 0 heights20_eq (by decide +kernel)
def row21 : Row 21 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 49, 46, 48])
def table22 : Table 22 := .push table21 row21
def counts22 : Fin 22 → Nat := extend counts21 1
theorem counts22_eq : Table.fold (fun _ => 1) nodeCountAlgebra table22 = counts22 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table21 row21 counts21 1 counts21_eq (by decide +kernel)
def heights22 : Fin 22 → Nat := extend heights21 0
theorem heights22_eq : Table.fold (fun _ => 0) heightAlgebra table22 = heights22 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table21 row21 heights21 0 heights21_eq (by decide +kernel)
def row22 : Row 22 := Row.scalar (Scalar.keyword [97, 115, 115, 117, 109, 112, 116, 105, 111, 110, 115])
def table23 : Table 23 := .push table22 row22
def counts23 : Fin 23 → Nat := extend counts22 1
theorem counts23_eq : Table.fold (fun _ => 1) nodeCountAlgebra table23 = counts23 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table22 row22 counts22 1 counts22_eq (by decide +kernel)
def heights23 : Fin 23 → Nat := extend heights22 0
theorem heights23_eq : Table.fold (fun _ => 0) heightAlgebra table23 = heights23 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table22 row22 heights22 0 heights22_eq (by decide +kernel)
def row23 : Row 23 := Row.scalar (Scalar.keyword [97, 108, 105, 99, 101])
def table24 : Table 24 := .push table23 row23
def counts24 : Fin 24 → Nat := extend counts23 1
theorem counts24_eq : Table.fold (fun _ => 1) nodeCountAlgebra table24 = counts24 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table23 row23 counts23 1 counts23_eq (by decide +kernel)
def heights24 : Fin 24 → Nat := extend heights23 0
theorem heights24_eq : Table.fold (fun _ => 0) heightAlgebra table24 = heights24 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table23 row23 heights23 0 heights23_eq (by decide +kernel)
def row24 : Row 24 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 49, 46, 49])
def table25 : Table 25 := .push table24 row24
def counts25 : Fin 25 → Nat := extend counts24 1
theorem counts25_eq : Table.fold (fun _ => 1) nodeCountAlgebra table25 = counts25 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table24 row24 counts24 1 counts24_eq (by decide +kernel)
def heights25 : Fin 25 → Nat := extend heights24 0
theorem heights25_eq : Table.fold (fun _ => 0) heightAlgebra table25 = heights25 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table24 row24 heights24 0 heights24_eq (by decide +kernel)
def row25 : Row 25 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 50, 46, 50])
def table26 : Table 26 := .push table25 row25
def counts26 : Fin 26 → Nat := extend counts25 1
theorem counts26_eq : Table.fold (fun _ => 1) nodeCountAlgebra table26 = counts26 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table25 row25 counts25 1 counts25_eq (by decide +kernel)
def heights26 : Fin 26 → Nat := extend heights25 0
theorem heights26_eq : Table.fold (fun _ => 0) heightAlgebra table26 = heights26 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table25 row25 heights25 0 heights25_eq (by decide +kernel)
def row26 : Row 26 := Row.scalar (Scalar.boolean true)
def table27 : Table 27 := .push table26 row26
def counts27 : Fin 27 → Nat := extend counts26 1
theorem counts27_eq : Table.fold (fun _ => 1) nodeCountAlgebra table27 = counts27 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table26 row26 counts26 1 counts26_eq (by decide +kernel)
def heights27 : Fin 27 → Nat := extend heights26 0
theorem heights27_eq : Table.fold (fun _ => 0) heightAlgebra table27 = heights27 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table26 row26 heights26 0 heights26_eq (by decide +kernel)
def row27 : Row 27 := Row.scalar (Scalar.keyword [111, 114])
def table28 : Table 28 := .push table27 row27
def counts28 : Fin 28 → Nat := extend counts27 1
theorem counts28_eq : Table.fold (fun _ => 1) nodeCountAlgebra table28 = counts28 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table27 row27 counts27 1 counts27_eq (by decide +kernel)
def heights28 : Fin 28 → Nat := extend heights27 0
theorem heights28_eq : Table.fold (fun _ => 0) heightAlgebra table28 = heights28 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table27 row27 heights27 0 heights27_eq (by decide +kernel)
def row28 : Row 28 := Row.scalar (Scalar.keyword [97, 114, 103, 115])
def table29 : Table 29 := .push table28 row28
def counts29 : Fin 29 → Nat := extend counts28 1
theorem counts29_eq : Table.fold (fun _ => 1) nodeCountAlgebra table29 = counts29 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table28 row28 counts28 1 counts28_eq (by decide +kernel)
def heights29 : Fin 29 → Nat := extend heights28 0
theorem heights29_eq : Table.fold (fun _ => 0) heightAlgebra table29 = heights29 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table28 row28 heights28 0 heights28_eq (by decide +kernel)
def row29 : Row 29 := Row.scalar (Scalar.keyword [112, 114, 111, 118, 101])
def table30 : Table 30 := .push table29 row29
def counts30 : Fin 30 → Nat := extend counts29 1
theorem counts30_eq : Table.fold (fun _ => 1) nodeCountAlgebra table30 = counts30 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table29 row29 counts29 1 counts29_eq (by decide +kernel)
def heights30 : Fin 30 → Nat := extend heights29 0
theorem heights30_eq : Table.fold (fun _ => 0) heightAlgebra table30 = heights30 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table29 row29 heights29 0 heights29_eq (by decide +kernel)
def row30 : Row 30 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 48, 46, 48])
def table31 : Table 31 := .push table30 row30
def counts31 : Fin 31 → Nat := extend counts30 1
theorem counts31_eq : Table.fold (fun _ => 1) nodeCountAlgebra table31 = counts31 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table30 row30 counts30 1 counts30_eq (by decide +kernel)
def heights31 : Fin 31 → Nat := extend heights30 0
theorem heights31_eq : Table.fold (fun _ => 0) heightAlgebra table31 = heights31 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table30 row30 heights30 0 heights30_eq (by decide +kernel)
def row31 : Row 31 := Row.scalar (Scalar.keyword [99, 108, 97, 105, 109])
def table32 : Table 32 := .push table31 row31
def counts32 : Fin 32 → Nat := extend counts31 1
theorem counts32_eq : Table.fold (fun _ => 1) nodeCountAlgebra table32 = counts32 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table31 row31 counts31 1 counts31_eq (by decide +kernel)
def heights32 : Fin 32 → Nat := extend heights31 0
theorem heights32_eq : Table.fold (fun _ => 0) heightAlgebra table32 = heights32 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table31 row31 heights31 0 heights31_eq (by decide +kernel)
def row32 : Row 32 := Row.scalar (Scalar.keyword [99, 97, 114, 111, 108])
def table33 : Table 33 := .push table32 row32
def counts33 : Fin 33 → Nat := extend counts32 1
theorem counts33_eq : Table.fold (fun _ => 1) nodeCountAlgebra table33 = counts33 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table32 row32 counts32 1 counts32_eq (by decide +kernel)
def heights33 : Fin 33 → Nat := extend heights32 0
theorem heights33_eq : Table.fold (fun _ => 0) heightAlgebra table33 = heights33 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table32 row32 heights32 0 heights32_eq (by decide +kernel)
def row33 : Row 33 := Row.scalar (Scalar.keyword [102, 111, 114, 109, 97, 108, 47, 113, 117, 101, 114, 121])
def table34 : Table 34 := .push table33 row33
def counts34 : Fin 34 → Nat := extend counts33 1
theorem counts34_eq : Table.fold (fun _ => 1) nodeCountAlgebra table34 = counts34 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table33 row33 counts33 1 counts33_eq (by decide +kernel)
def heights34 : Fin 34 → Nat := extend heights33 0
theorem heights34_eq : Table.fold (fun _ => 0) heightAlgebra table34 = heights34 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table33 row33 heights33 0 heights33_eq (by decide +kernel)
def row34 : Row 34 := Row.scalar (Scalar.keyword [102, 111, 114, 109, 97, 108, 47, 102, 105, 110, 105, 116, 101, 45, 114, 101, 108, 97, 116, 105, 111, 110, 45, 118, 49])
def table35 : Table 35 := .push table34 row34
def counts35 : Fin 35 → Nat := extend counts34 1
theorem counts35_eq : Table.fold (fun _ => 1) nodeCountAlgebra table35 = counts35 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table34 row34 counts34 1 counts34_eq (by decide +kernel)
def heights35 : Fin 35 → Nat := extend heights34 0
theorem heights35_eq : Table.fold (fun _ => 0) heightAlgebra table35 = heights35 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table34 row34 heights34 0 heights34_eq (by decide +kernel)
def row35 : Row 35 := Row.node (Kind.map 0) (fun (slot : Fin 0 × Bool) => if slot.2 then (List.get ([] : List (Fin 35))) slot.1 else (List.get ([] : List (Fin 35))) slot.1)
def table36 : Table 36 := .push table35 row35
def counts36 : Fin 36 → Nat := extend counts35 1
theorem counts36_eq : Table.fold (fun _ => 1) nodeCountAlgebra table36 = counts36 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table35 row35 counts35 1 counts35_eq (by decide +kernel)
def heights36 : Fin 36 → Nat := extend heights35 0
theorem heights36_eq : Table.fold (fun _ => 0) heightAlgebra table36 = heights36 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table35 row35 heights35 0 heights35_eq (by decide +kernel)
def row36 : Row 36 := Row.scalar (Scalar.keyword [102, 111, 114, 109, 97, 108, 47, 118, 97, 108, 117, 101])
def table37 : Table 37 := .push table36 row36
def counts37 : Fin 37 → Nat := extend counts36 1
theorem counts37_eq : Table.fold (fun _ => 1) nodeCountAlgebra table37 = counts37 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table36 row36 counts36 1 counts36_eq (by decide +kernel)
def heights37 : Fin 37 → Nat := extend heights36 0
theorem heights37_eq : Table.fold (fun _ => 0) heightAlgebra table37 = heights37 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table36 row36 heights36 0 heights36_eq (by decide +kernel)
def row37 : Row 37 := Row.scalar (Scalar.bytes [103, 111, 97, 108, 47, 99, 111, 117, 110, 116, 101, 114, 101, 120, 97, 109, 112, 108, 101])
def table38 : Table 38 := .push table37 row37
def counts38 : Fin 38 → Nat := extend counts37 1
theorem counts38_eq : Table.fold (fun _ => 1) nodeCountAlgebra table38 = counts38 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table37 row37 counts37 1 counts37_eq (by decide +kernel)
def heights38 : Fin 38 → Nat := extend heights37 0
theorem heights38_eq : Table.fold (fun _ => 0) heightAlgebra table38 = heights38 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table37 row37 heights37 0 heights37_eq (by decide +kernel)
def row38 : Row 38 := Row.scalar (Scalar.keyword [98, 108, 47, 99, 97, 110, 111, 110, 105, 99, 97, 108, 45, 102, 111, 114, 109, 97, 108, 45, 100, 97, 116, 97, 45, 118, 49])
def table39 : Table 39 := .push table38 row38
def counts39 : Fin 39 → Nat := extend counts38 1
theorem counts39_eq : Table.fold (fun _ => 1) nodeCountAlgebra table39 = counts39 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table38 row38 counts38 1 counts38_eq (by decide +kernel)
def heights39 : Fin 39 → Nat := extend heights38 0
theorem heights39_eq : Table.fold (fun _ => 0) heightAlgebra table39 = heights39 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table38 row38 heights38 0 heights38_eq (by decide +kernel)
def row39 : Row 39 := Row.scalar (Scalar.keyword [115, 99, 111, 112, 101])
def table40 : Table 40 := .push table39 row39
def counts40 : Fin 40 → Nat := extend counts39 1
theorem counts40_eq : Table.fold (fun _ => 1) nodeCountAlgebra table40 = counts40 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table39 row39 counts39 1 counts39_eq (by decide +kernel)
def heights40 : Fin 40 → Nat := extend heights39 0
theorem heights40_eq : Table.fold (fun _ => 0) heightAlgebra table40 = heights40 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table39 row39 heights39 0 heights39_eq (by decide +kernel)
def row40 : Row 40 := Row.scalar (Scalar.keyword [99, 111, 110, 115, 116, 114, 97, 105, 110, 116, 115])
def table41 : Table 41 := .push table40 row40
def counts41 : Fin 41 → Nat := extend counts40 1
theorem counts41_eq : Table.fold (fun _ => 1) nodeCountAlgebra table41 = counts41 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table40 row40 counts40 1 counts40_eq (by decide +kernel)
def heights41 : Fin 41 → Nat := extend heights40 0
theorem heights41_eq : Table.fold (fun _ => 0) heightAlgebra table41 = heights41 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table40 row40 heights40 0 heights40_eq (by decide +kernel)
def row41 : Row 41 := Row.scalar (Scalar.keyword [115, 111, 114, 116])
def table42 : Table 42 := .push table41 row41
def counts42 : Fin 42 → Nat := extend counts41 1
theorem counts42_eq : Table.fold (fun _ => 1) nodeCountAlgebra table42 = counts42 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table41 row41 counts41 1 counts41_eq (by decide +kernel)
def heights42 : Fin 42 → Nat := extend heights41 0
theorem heights42_eq : Table.fold (fun _ => 0) heightAlgebra table42 = heights42 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table41 row41 heights41 0 heights41_eq (by decide +kernel)
def row42 : Row 42 := Row.scalar (Scalar.keyword [98, 111, 98])
def table43 : Table 43 := .push table42 row42
def counts43 : Fin 43 → Nat := extend counts42 1
theorem counts43_eq : Table.fold (fun _ => 1) nodeCountAlgebra table43 = counts43 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table42 row42 counts42 1 counts42_eq (by decide +kernel)
def heights43 : Fin 43 → Nat := extend heights42 0
theorem heights43_eq : Table.fold (fun _ => 0) heightAlgebra table43 = heights43 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table42 row42 heights42 0 heights42_eq (by decide +kernel)
def row43 : Row 43 := Row.scalar (Scalar.keyword [100, 111, 109, 97, 105, 110])
def table44 : Table 44 := .push table43 row43
def counts44 : Fin 44 → Nat := extend counts43 1
theorem counts44_eq : Table.fold (fun _ => 1) nodeCountAlgebra table44 = counts44 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table43 row43 counts43 1 counts43_eq (by decide +kernel)
def heights44 : Fin 44 → Nat := extend heights43 0
theorem heights44_eq : Table.fold (fun _ => 0) heightAlgebra table44 = heights44 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table43 row43 heights43 0 heights43_eq (by decide +kernel)
def row44 : Row 44 := Row.scalar (Scalar.keyword [112, 114, 111, 102, 105, 108, 101])
def table45 : Table 45 := .push table44 row44
def counts45 : Fin 45 → Nat := extend counts44 1
theorem counts45_eq : Table.fold (fun _ => 1) nodeCountAlgebra table45 = counts45 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table44 row44 counts44 1 counts44_eq (by decide +kernel)
def heights45 : Fin 45 → Nat := extend heights44 0
theorem heights45_eq : Table.fold (fun _ => 0) heightAlgebra table45 = heights45 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table44 row44 heights44 0 heights44_eq (by decide +kernel)
def row45 : Row 45 := Row.scalar (Scalar.nil)
def table46 : Table 46 := .push table45 row45
def counts46 : Fin 46 → Nat := extend counts45 1
theorem counts46_eq : Table.fold (fun _ => 1) nodeCountAlgebra table46 = counts46 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table45 row45 counts45 1 counts45_eq (by decide +kernel)
def heights46 : Fin 46 → Nat := extend heights45 0
theorem heights46_eq : Table.fold (fun _ => 0) heightAlgebra table46 = heights46 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table45 row45 heights45 0 heights45_eq (by decide +kernel)
def row46 : Row 46 := Row.scalar (Scalar.keyword [107, 101, 121, 115])
def table47 : Table 47 := .push table46 row46
def counts47 : Fin 47 → Nat := extend counts46 1
theorem counts47_eq : Table.fold (fun _ => 1) nodeCountAlgebra table47 = counts47 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table46 row46 counts46 1 counts46_eq (by decide +kernel)
def heights47 : Fin 47 → Nat := extend heights46 0
theorem heights47_eq : Table.fold (fun _ => 0) heightAlgebra table47 = heights47 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table46 row46 heights46 0 heights46_eq (by decide +kernel)
def row47 : Row 47 := Row.scalar (Scalar.keyword [97, 115, 115, 101, 114, 116, 105, 111, 110, 115])
def table48 : Table 48 := .push table47 row47
def counts48 : Fin 48 → Nat := extend counts47 1
theorem counts48_eq : Table.fold (fun _ => 1) nodeCountAlgebra table48 = counts48 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table47 row47 counts47 1 counts47_eq (by decide +kernel)
def heights48 : Fin 48 → Nat := extend heights47 0
theorem heights48_eq : Table.fold (fun _ => 0) heightAlgebra table48 = heights48 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table47 row47 heights47 0 heights47_eq (by decide +kernel)
def row48 : Row 48 := Row.node (Kind.vector 0) (List.get ([] : List (Fin 48)))
def table49 : Table 49 := .push table48 row48
def counts49 : Fin 49 → Nat := extend counts48 1
theorem counts49_eq : Table.fold (fun _ => 1) nodeCountAlgebra table49 = counts49 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table48 row48 counts48 1 counts48_eq (by decide +kernel)
def heights49 : Fin 49 → Nat := extend heights48 0
theorem heights49_eq : Table.fold (fun _ => 0) heightAlgebra table49 = heights49 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table48 row48 heights48 0 heights48_eq (by decide +kernel)
def row49 : Row 49 := Row.scalar (Scalar.keyword [114, 101, 108, 97, 116, 105, 111, 110, 47, 99, 108, 111, 115, 117, 114, 101, 45, 105, 115, 45, 116, 114, 97, 110, 115, 105, 116, 105, 118, 101])
def table50 : Table 50 := .push table49 row49
def counts50 : Fin 50 → Nat := extend counts49 1
theorem counts50_eq : Table.fold (fun _ => 1) nodeCountAlgebra table50 = counts50 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table49 row49 counts49 1 counts49_eq (by decide +kernel)
def heights50 : Fin 50 → Nat := extend heights49 0
theorem heights50_eq : Table.fold (fun _ => 0) heightAlgebra table50 = heights50 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table49 row49 heights49 0 heights49_eq (by decide +kernel)
def row50 : Row 50 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 50, 46, 49])
def table51 : Table 51 := .push table50 row50
def counts51 : Fin 51 → Nat := extend counts50 1
theorem counts51_eq : Table.fold (fun _ => 1) nodeCountAlgebra table51 = counts51 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table50 row50 counts50 1 counts50_eq (by decide +kernel)
def heights51 : Fin 51 → Nat := extend heights50 0
theorem heights51_eq : Table.fold (fun _ => 0) heightAlgebra table51 = heights51 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table50 row50 heights50 0 heights50_eq (by decide +kernel)
def row51 : Row 51 := Row.scalar (Scalar.keyword [118, 97, 99, 117, 105, 116, 121])
def table52 : Table 52 := .push table51 row51
def counts52 : Fin 52 → Nat := extend counts51 1
theorem counts52_eq : Table.fold (fun _ => 1) nodeCountAlgebra table52 = counts52 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table51 row51 counts51 1 counts51_eq (by decide +kernel)
def heights52 : Fin 52 → Nat := extend heights51 0
theorem heights52_eq : Table.fold (fun _ => 0) heightAlgebra table52 = heights52 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table51 row51 heights51 0 heights51_eq (by decide +kernel)
def row52 : Row 52 := Row.scalar (Scalar.keyword [119, 105, 116, 104, 105, 110])
def table53 : Table 53 := .push table52 row52
def counts53 : Fin 53 → Nat := extend counts52 1
theorem counts53_eq : Table.fold (fun _ => 1) nodeCountAlgebra table53 = counts53 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table52 row52 counts52 1 counts52_eq (by decide +kernel)
def heights53 : Fin 53 → Nat := extend heights52 0
theorem heights53_eq : Table.fold (fun _ => 0) heightAlgebra table53 = heights53 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table52 row52 heights52 0 heights52_eq (by decide +kernel)
def row53 : Row 53 := Row.scalar (Scalar.keyword [100, 101, 102, 105, 110, 101, 100])
def table54 : Table 54 := .push table53 row53
def counts54 : Fin 54 → Nat := extend counts53 1
theorem counts54_eq : Table.fold (fun _ => 1) nodeCountAlgebra table54 = counts54 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table53 row53 counts53 1 counts53_eq (by decide +kernel)
def heights54 : Fin 54 → Nat := extend heights53 0
theorem heights54_eq : Table.fold (fun _ => 0) heightAlgebra table54 = heights54 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table53 row53 heights53 0 heights53_eq (by decide +kernel)
def row54 : Row 54 := Row.scalar (Scalar.keyword [102, 105, 110, 105, 116, 101, 45, 117, 110, 105, 118, 101, 114, 115, 101])
def table55 : Table 55 := .push table54 row54
def counts55 : Fin 55 → Nat := extend counts54 1
theorem counts55_eq : Table.fold (fun _ => 1) nodeCountAlgebra table55 = counts55 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table54 row54 counts54 1 counts54_eq (by decide +kernel)
def heights55 : Fin 55 → Nat := extend heights54 0
theorem heights55_eq : Table.fold (fun _ => 0) heightAlgebra table55 = heights55 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table54 row54 heights54 0 heights54_eq (by decide +kernel)
def row55 : Row 55 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 48, 46, 49])
def table56 : Table 56 := .push table55 row55
def counts56 : Fin 56 → Nat := extend counts55 1
theorem counts56_eq : Table.fold (fun _ => 1) nodeCountAlgebra table56 = counts56 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table55 row55 counts55 1 counts55_eq (by decide +kernel)
def heights56 : Fin 56 → Nat := extend heights55 0
theorem heights56_eq : Table.fold (fun _ => 0) heightAlgebra table56 = heights56 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table55 row55 heights55 0 heights55_eq (by decide +kernel)
def row56 : Row 56 := Row.scalar (Scalar.keyword [97, 110, 100])
def table57 : Table 57 := .push table56 row56
def counts57 : Fin 57 → Nat := extend counts56 1
theorem counts57_eq : Table.fold (fun _ => 1) nodeCountAlgebra table57 = counts57 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table56 row56 counts56 1 counts56_eq (by decide +kernel)
def heights57 : Fin 57 → Nat := extend heights56 0
theorem heights57_eq : Table.fold (fun _ => 0) heightAlgebra table57 = heights57 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table56 row56 heights56 0 heights56_eq (by decide +kernel)
def row57 : Row 57 := Row.scalar (Scalar.keyword [114, 101, 108, 97, 116, 105, 111, 110])
def table58 : Table 58 := .push table57 row57
def counts58 : Fin 58 → Nat := extend counts57 1
theorem counts58_eq : Table.fold (fun _ => 1) nodeCountAlgebra table58 = counts58 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table57 row57 counts57 1 counts57_eq (by decide +kernel)
def heights58 : Fin 58 → Nat := extend heights57 0
theorem heights58_eq : Table.fold (fun _ => 0) heightAlgebra table58 = heights58 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table57 row57 heights57 0 heights57_eq (by decide +kernel)
def row58 : Row 58 := Row.scalar (Scalar.bytes [101, 100, 103, 101, 115])
def table59 : Table 59 := .push table58 row58
def counts59 : Fin 59 → Nat := extend counts58 1
theorem counts59_eq : Table.fold (fun _ => 1) nodeCountAlgebra table59 = counts59 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table58 row58 counts58 1 counts58_eq (by decide +kernel)
def heights59 : Fin 59 → Nat := extend heights58 0
theorem heights59_eq : Table.fold (fun _ => 0) heightAlgebra table59 = heights59 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table58 row58 heights58 0 heights58_eq (by decide +kernel)
def row59 : Row 59 := Row.scalar (Scalar.keyword [109, 111, 100, 101])
def table60 : Table 60 := .push table59 row59
def counts60 : Fin 60 → Nat := extend counts59 1
theorem counts60_eq : Table.fold (fun _ => 1) nodeCountAlgebra table60 = counts60 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table59 row59 counts59 1 counts59_eq (by decide +kernel)
def heights60 : Fin 60 → Nat := extend heights59 0
theorem heights60_eq : Table.fold (fun _ => 0) heightAlgebra table60 = heights60 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table59 row59 heights59 0 heights59_eq (by decide +kernel)
def row60 : Row 60 := Row.scalar (Scalar.keyword [111, 98, 115, 101, 114, 118, 101])
def table61 : Table 61 := .push table60 row60
def counts61 : Fin 61 → Nat := extend counts60 1
theorem counts61_eq : Table.fold (fun _ => 1) nodeCountAlgebra table61 = counts61 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table60 row60 counts60 1 counts60_eq (by decide +kernel)
def heights61 : Fin 61 → Nat := extend heights60 0
theorem heights61_eq : Table.fold (fun _ => 0) heightAlgebra table61 = heights61 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table60 row60 heights60 0 heights60_eq (by decide +kernel)
def row61 : Row 61 := Row.scalar (Scalar.bytes [119, 105, 116, 104, 105, 110, 47, 48])
def table62 : Table 62 := .push table61 row61
def counts62 : Fin 62 → Nat := extend counts61 1
theorem counts62_eq : Table.fold (fun _ => 1) nodeCountAlgebra table62 = counts62 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table61 row61 counts61 1 counts61_eq (by decide +kernel)
def heights62 : Fin 62 → Nat := extend heights61 0
theorem heights62_eq : Table.fold (fun _ => 0) heightAlgebra table62 = heights62 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table61 row61 heights61 0 heights61_eq (by decide +kernel)
def row62 : Row 62 := Row.scalar (Scalar.keyword [114, 101, 112, 111, 114, 116])
def table63 : Table 63 := .push table62 row62
def counts63 : Fin 63 → Nat := extend counts62 1
theorem counts63_eq : Table.fold (fun _ => 1) nodeCountAlgebra table63 = counts63 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table62 row62 counts62 1 counts62_eq (by decide +kernel)
def heights63 : Fin 63 → Nat := extend heights62 0
theorem heights63_eq : Table.fold (fun _ => 0) heightAlgebra table63 = heights63 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table62 row62 heights62 0 heights62_eq (by decide +kernel)
def row63 : Row 63 := Row.scalar (Scalar.keyword [101, 100, 103, 101, 115])
def table64 : Table 64 := .push table63 row63
def counts64 : Fin 64 → Nat := extend counts63 1
theorem counts64_eq : Table.fold (fun _ => 1) nodeCountAlgebra table64 = counts64 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table63 row63 counts63 1 counts63_eq (by decide +kernel)
def heights64 : Fin 64 → Nat := extend heights63 0
theorem heights64_eq : Table.fold (fun _ => 0) heightAlgebra table64 = heights64 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table63 row63 heights63 0 heights63_eq (by decide +kernel)
def row64 : Row 64 := Row.scalar (Scalar.keyword [99, 111, 117, 110, 116, 101, 114, 101, 120, 97, 109, 112, 108, 101])
def table65 : Table 65 := .push table64 row64
def counts65 : Fin 65 → Nat := extend counts64 1
theorem counts65_eq : Table.fold (fun _ => 1) nodeCountAlgebra table65 = counts65 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table64 row64 counts64 1 counts64_eq (by decide +kernel)
def heights65 : Fin 65 → Nat := extend heights64 0
theorem heights65_eq : Table.fold (fun _ => 0) heightAlgebra table65 = heights65 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table64 row64 heights64 0 heights64_eq (by decide +kernel)
def row65 : Row 65 := Row.scalar (Scalar.keyword [100, 97, 116, 97])
def table66 : Table 66 := .push table65 row65
def counts66 : Fin 66 → Nat := extend counts65 1
theorem counts66_eq : Table.fold (fun _ => 1) nodeCountAlgebra table66 = counts66 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table65 row65 counts65 1 counts65_eq (by decide +kernel)
def heights66 : Fin 66 → Nat := extend heights65 0
theorem heights66_eq : Table.fold (fun _ => 0) heightAlgebra table66 = heights66 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table65 row65 heights65 0 heights65_eq (by decide +kernel)
def row66 : Row 66 := Row.scalar (Scalar.keyword [105, 109, 112, 108, 105, 101, 115])
def table67 : Table 67 := .push table66 row66
def counts67 : Fin 67 → Nat := extend counts66 1
theorem counts67_eq : Table.fold (fun _ => 1) nodeCountAlgebra table67 = counts67 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table66 row66 counts66 1 counts66_eq (by decide +kernel)
def heights67 : Fin 67 → Nat := extend heights66 0
theorem heights67_eq : Table.fold (fun _ => 0) heightAlgebra table67 = heights67 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table66 row66 heights66 0 heights66_eq (by decide +kernel)
def row67 : Row 67 := Row.scalar (Scalar.keyword [111, 112])
def table68 : Table 68 := .push table67 row67
def counts68 : Fin 68 → Nat := extend counts67 1
theorem counts68_eq : Table.fold (fun _ => 1) nodeCountAlgebra table68 = counts68 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table67 row67 counts67 1 counts67_eq (by decide +kernel)
def heights68 : Fin 68 → Nat := extend heights67 0
theorem heights68_eq : Table.fold (fun _ => 0) heightAlgebra table68 = heights68 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table67 row67 heights67 0 heights67_eq (by decide +kernel)
def row68 : Row 68 := Row.scalar (Scalar.keyword [105, 100, 101, 110, 116, 105, 116, 121, 45, 112, 114, 111, 102, 105, 108, 101])
def table69 : Table 69 := .push table68 row68
def counts69 : Fin 69 → Nat := extend counts68 1
theorem counts69_eq : Table.fold (fun _ => 1) nodeCountAlgebra table69 = counts69 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table68 row68 counts68 1 counts68_eq (by decide +kernel)
def heights69 : Fin 69 → Nat := extend heights68 0
theorem heights69_eq : Table.fold (fun _ => 0) heightAlgebra table69 = heights69 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table68 row68 heights68 0 heights68_eq (by decide +kernel)
def row69 : Row 69 := Row.scalar (Scalar.bytes [103, 114, 97, 112, 104, 46, 48, 46, 50])
def table70 : Table 70 := .push table69 row69
def counts70 : Fin 70 → Nat := extend counts69 1
theorem counts70_eq : Table.fold (fun _ => 1) nodeCountAlgebra table70 = counts70 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table69 row69 counts69 1 counts69_eq (by decide +kernel)
def heights70 : Fin 70 → Nat := extend heights69 0
theorem heights70_eq : Table.fold (fun _ => 0) heightAlgebra table70 = heights70 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table69 row69 heights69 0 heights69_eq (by decide +kernel)
def row70 : Row 70 := Row.node (Kind.map 2) (fun (slot : Fin 2 × Bool) => if slot.2 then (List.get ([⟨45, by decide⟩, ⟨61, by decide⟩] : List (Fin 70))) slot.1 else (List.get ([⟨11, by decide⟩, ⟨15, by decide⟩] : List (Fin 70))) slot.1)
def table71 : Table 71 := .push table70 row70
def counts71 : Fin 71 → Nat := extend counts70 5
theorem counts71_eq : Table.fold (fun _ => 1) nodeCountAlgebra table71 = counts71 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table70 row70 counts70 5 counts70_eq (by decide +kernel)
def heights71 : Fin 71 → Nat := extend heights70 1
theorem heights71_eq : Table.fold (fun _ => 0) heightAlgebra table71 = heights71 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table70 row70 heights70 1 heights70_eq (by decide +kernel)
def row71 : Row 71 := Row.node (Kind.vector 1) (List.get ([⟨12, by decide⟩] : List (Fin 71)))
def table72 : Table 72 := .push table71 row71
def counts72 : Fin 72 → Nat := extend counts71 2
theorem counts72_eq : Table.fold (fun _ => 1) nodeCountAlgebra table72 = counts72 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table71 row71 counts71 2 counts71_eq (by decide +kernel)
def heights72 : Fin 72 → Nat := extend heights71 1
theorem heights72_eq : Table.fold (fun _ => 0) heightAlgebra table72 = heights72 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table71 row71 heights71 1 heights71_eq (by decide +kernel)
def row72 : Row 72 := Row.node (Kind.vector 1) (List.get ([⟨3, by decide⟩] : List (Fin 72)))
def table73 : Table 73 := .push table72 row72
def counts73 : Fin 73 → Nat := extend counts72 2
theorem counts73_eq : Table.fold (fun _ => 1) nodeCountAlgebra table73 = counts73 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table72 row72 counts72 2 counts72_eq (by decide +kernel)
def heights73 : Fin 73 → Nat := extend heights72 1
theorem heights73_eq : Table.fold (fun _ => 0) heightAlgebra table73 = heights73 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table72 row72 heights72 1 heights72_eq (by decide +kernel)
def row73 : Row 73 := Row.node (Kind.vector 3) (List.get ([⟨23, by decide⟩, ⟨42, by decide⟩, ⟨32, by decide⟩] : List (Fin 73)))
def table74 : Table 74 := .push table73 row73
def counts74 : Fin 74 → Nat := extend counts73 4
theorem counts74_eq : Table.fold (fun _ => 1) nodeCountAlgebra table74 = counts74 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table73 row73 counts73 4 counts73_eq (by decide +kernel)
def heights74 : Fin 74 → Nat := extend heights73 1
theorem heights74_eq : Table.fold (fun _ => 0) heightAlgebra table74 = heights74 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table73 row73 heights73 1 heights73_eq (by decide +kernel)
def row74 : Row 74 := Row.node (Kind.map 2) (fun (slot : Fin 2 × Bool) => if slot.2 then (List.get ([⟨45, by decide⟩, ⟨0, by decide⟩] : List (Fin 74))) slot.1 else (List.get ([⟨11, by decide⟩, ⟨15, by decide⟩] : List (Fin 74))) slot.1)
def table75 : Table 75 := .push table74 row74
def counts75 : Fin 75 → Nat := extend counts74 5
theorem counts75_eq : Table.fold (fun _ => 1) nodeCountAlgebra table75 = counts75 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table74 row74 counts74 5 counts74_eq (by decide +kernel)
def heights75 : Fin 75 → Nat := extend heights74 1
theorem heights75_eq : Table.fold (fun _ => 0) heightAlgebra table75 = heights75 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table74 row74 heights74 1 heights74_eq (by decide +kernel)
def row75 : Row 75 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨21, by decide⟩, ⟨4, by decide⟩] : List (Fin 75))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 75))) slot.1)
def table76 : Table 76 := .push table75 row75
def counts76 : Fin 76 → Nat := extend counts75 12
theorem counts76_eq : Table.fold (fun _ => 1) nodeCountAlgebra table76 = counts76 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table75 row75 counts75 12 counts75_eq (by decide +kernel)
def heights76 : Fin 76 → Nat := extend heights75 2
theorem heights76_eq : Table.fold (fun _ => 0) heightAlgebra table76 = heights76 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table75 row75 heights75 2 heights75_eq (by decide +kernel)
def row76 : Row 76 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨69, by decide⟩, ⟨4, by decide⟩] : List (Fin 76))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 76))) slot.1)
def table77 : Table 77 := .push table76 row76
def counts77 : Fin 77 → Nat := extend counts76 12
theorem counts77_eq : Table.fold (fun _ => 1) nodeCountAlgebra table77 = counts77 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table76 row76 counts76 12 counts76_eq (by decide +kernel)
def heights77 : Fin 77 → Nat := extend heights76 2
theorem heights77_eq : Table.fold (fun _ => 0) heightAlgebra table77 = heights77 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table76 row76 heights76 2 heights76_eq (by decide +kernel)
def row77 : Row 77 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨55, by decide⟩, ⟨4, by decide⟩] : List (Fin 77))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 77))) slot.1)
def table78 : Table 78 := .push table77 row77
def counts78 : Fin 78 → Nat := extend counts77 12
theorem counts78_eq : Table.fold (fun _ => 1) nodeCountAlgebra table78 = counts78 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table77 row77 counts77 12 counts77_eq (by decide +kernel)
def heights78 : Fin 78 → Nat := extend heights77 2
theorem heights78_eq : Table.fold (fun _ => 0) heightAlgebra table78 = heights78 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table77 row77 heights77 2 heights77_eq (by decide +kernel)
def row78 : Row 78 := Row.node (Kind.map 2) (fun (slot : Fin 2 × Bool) => if slot.2 then (List.get ([⟨73, by decide⟩, ⟨54, by decide⟩] : List (Fin 78))) slot.1 else (List.get ([⟨2, by decide⟩, ⟨59, by decide⟩] : List (Fin 78))) slot.1)
def table79 : Table 79 := .push table78 row78
def counts79 : Fin 79 → Nat := extend counts78 8
theorem counts79_eq : Table.fold (fun _ => 1) nodeCountAlgebra table79 = counts79 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table78 row78 counts78 8 counts78_eq (by decide +kernel)
def heights79 : Fin 79 → Nat := extend heights78 2
theorem heights79_eq : Table.fold (fun _ => 0) heightAlgebra table79 = heights79 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table78 row78 heights78 2 heights78_eq (by decide +kernel)
def row79 : Row 79 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨18, by decide⟩, ⟨4, by decide⟩] : List (Fin 79))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 79))) slot.1)
def table80 : Table 80 := .push table79 row79
def counts80 : Fin 80 → Nat := extend counts79 12
theorem counts80_eq : Table.fold (fun _ => 1) nodeCountAlgebra table80 = counts80 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table79 row79 counts79 12 counts79_eq (by decide +kernel)
def heights80 : Fin 80 → Nat := extend heights79 2
theorem heights80_eq : Table.fold (fun _ => 0) heightAlgebra table80 = heights80 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table79 row79 heights79 2 heights79_eq (by decide +kernel)
def row80 : Row 80 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨25, by decide⟩, ⟨4, by decide⟩] : List (Fin 80))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 80))) slot.1)
def table81 : Table 81 := .push table80 row80
def counts81 : Fin 81 → Nat := extend counts80 12
theorem counts81_eq : Table.fold (fun _ => 1) nodeCountAlgebra table81 = counts81 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table80 row80 counts80 12 counts80_eq (by decide +kernel)
def heights81 : Fin 81 → Nat := extend heights80 2
theorem heights81_eq : Table.fold (fun _ => 0) heightAlgebra table81 = heights81 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table80 row80 heights80 2 heights80_eq (by decide +kernel)
def row81 : Row 81 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨24, by decide⟩, ⟨4, by decide⟩] : List (Fin 81))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 81))) slot.1)
def table82 : Table 82 := .push table81 row81
def counts82 : Fin 82 → Nat := extend counts81 12
theorem counts82_eq : Table.fold (fun _ => 1) nodeCountAlgebra table82 = counts82 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table81 row81 counts81 12 counts81_eq (by decide +kernel)
def heights82 : Fin 82 → Nat := extend heights81 2
theorem heights82_eq : Table.fold (fun _ => 0) heightAlgebra table82 = heights82 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table81 row81 heights81 2 heights81_eq (by decide +kernel)
def row82 : Row 82 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨50, by decide⟩, ⟨4, by decide⟩] : List (Fin 82))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 82))) slot.1)
def table83 : Table 83 := .push table82 row82
def counts83 : Fin 83 → Nat := extend counts82 12
theorem counts83_eq : Table.fold (fun _ => 1) nodeCountAlgebra table83 = counts83 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table82 row82 counts82 12 counts82_eq (by decide +kernel)
def heights83 : Fin 83 → Nat := extend heights82 2
theorem heights83_eq : Table.fold (fun _ => 0) heightAlgebra table83 = heights83 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table82 row82 heights82 2 heights82_eq (by decide +kernel)
def row83 : Row 83 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨30, by decide⟩, ⟨4, by decide⟩] : List (Fin 83))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 83))) slot.1)
def table84 : Table 84 := .push table83 row83
def counts84 : Fin 84 → Nat := extend counts83 12
theorem counts84_eq : Table.fold (fun _ => 1) nodeCountAlgebra table84 = counts84 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table83 row83 counts83 12 counts83_eq (by decide +kernel)
def heights84 : Fin 84 → Nat := extend heights83 2
theorem heights84_eq : Table.fold (fun _ => 0) heightAlgebra table84 = heights84 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table83 row83 heights83 2 heights83_eq (by decide +kernel)
def row84 : Row 84 := Row.node (Kind.vector 2) (List.get ([⟨70, by decide⟩, ⟨74, by decide⟩] : List (Fin 84)))
def table85 : Table 85 := .push table84 row84
def counts85 : Fin 85 → Nat := extend counts84 11
theorem counts85_eq : Table.fold (fun _ => 1) nodeCountAlgebra table85 = counts85 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table84 row84 counts84 11 counts84_eq (by decide +kernel)
def heights85 : Fin 85 → Nat := extend heights84 2
theorem heights85_eq : Table.fold (fun _ => 0) heightAlgebra table85 = heights85 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table84 row84 heights84 2 heights84_eq (by decide +kernel)
def row85 : Row 85 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨26, by decide⟩, ⟨12, by decide⟩] : List (Fin 85))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 85))) slot.1)
def table86 : Table 86 := .push table85 row85
def counts86 : Fin 86 → Nat := extend counts85 12
theorem counts86_eq : Table.fold (fun _ => 1) nodeCountAlgebra table86 = counts86 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table85 row85 counts85 12 counts85_eq (by decide +kernel)
def heights86 : Fin 86 → Nat := extend heights85 2
theorem heights86_eq : Table.fold (fun _ => 0) heightAlgebra table86 = heights86 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table85 row85 heights85 2 heights85_eq (by decide +kernel)
def row86 : Row 86 := Row.node (Kind.map 3) (fun (slot : Fin 3 × Bool) => if slot.2 then (List.get ([⟨20, by decide⟩, ⟨34, by decide⟩, ⟨73, by decide⟩] : List (Fin 86))) slot.1 else (List.get ([⟨1, by decide⟩, ⟨44, by decide⟩, ⟨46, by decide⟩] : List (Fin 86))) slot.1)
def table87 : Table 87 := .push table86 row86
def counts87 : Fin 87 → Nat := extend counts86 10
theorem counts87_eq : Table.fold (fun _ => 1) nodeCountAlgebra table87 = counts87 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table86 row86 counts86 10 counts86_eq (by decide +kernel)
def heights87 : Fin 87 → Nat := extend heights86 2
theorem heights87_eq : Table.fold (fun _ => 0) heightAlgebra table87 = heights87 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table86 row86 heights86 2 heights86_eq (by decide +kernel)
def row87 : Row 87 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨48, by decide⟩, ⟨71, by decide⟩, ⟨13, by decide⟩, ⟨4, by decide⟩] : List (Fin 87))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 87))) slot.1)
def table88 : Table 88 := .push table87 row87
def counts88 : Fin 88 → Nat := extend counts87 12
theorem counts88_eq : Table.fold (fun _ => 1) nodeCountAlgebra table88 = counts88 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table87 row87 counts87 12 counts87_eq (by decide +kernel)
def heights88 : Fin 88 → Nat := extend heights87 2
theorem heights88_eq : Table.fold (fun _ => 0) heightAlgebra table88 = heights88 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table87 row87 heights87 2 heights87_eq (by decide +kernel)
def row88 : Row 88 := Row.node (Kind.vector 2) (List.get ([⟨83, by decide⟩, ⟨77, by decide⟩] : List (Fin 88)))
def table89 : Table 89 := .push table88 row88
def counts89 : Fin 89 → Nat := extend counts88 25
theorem counts89_eq : Table.fold (fun _ => 1) nodeCountAlgebra table89 = counts89 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table88 row88 counts88 25 counts88_eq (by decide +kernel)
def heights89 : Fin 89 → Nat := extend heights88 3
theorem heights89_eq : Table.fold (fun _ => 0) heightAlgebra table89 = heights89 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table88 row88 heights88 3 heights88_eq (by decide +kernel)
def row89 : Row 89 := Row.node (Kind.vector 3) (List.get ([⟨75, by decide⟩, ⟨81, by decide⟩, ⟨87, by decide⟩] : List (Fin 89)))
def table90 : Table 90 := .push table89 row89
def counts90 : Fin 90 → Nat := extend counts89 37
theorem counts90_eq : Table.fold (fun _ => 1) nodeCountAlgebra table90 = counts90 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table89 row89 counts89 37 counts89_eq (by decide +kernel)
def heights90 : Fin 90 → Nat := extend heights89 3
theorem heights90_eq : Table.fold (fun _ => 0) heightAlgebra table90 = heights90 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table89 row89 heights89 3 heights89_eq (by decide +kernel)
def row90 : Row 90 := Row.node (Kind.vector 2) (List.get ([⟨75, by decide⟩, ⟨76, by decide⟩] : List (Fin 90)))
def table91 : Table 91 := .push table90 row90
def counts91 : Fin 91 → Nat := extend counts90 25
theorem counts91_eq : Table.fold (fun _ => 1) nodeCountAlgebra table91 = counts91 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table90 row90 counts90 25 counts90_eq (by decide +kernel)
def heights91 : Fin 91 → Nat := extend heights90 3
theorem heights91_eq : Table.fold (fun _ => 0) heightAlgebra table91 = heights91 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table90 row90 heights90 3 heights90_eq (by decide +kernel)
def row91 : Row 91 := Row.node (Kind.vector 2) (List.get ([⟨83, by decide⟩, ⟨83, by decide⟩] : List (Fin 91)))
def table92 : Table 92 := .push table91 row91
def counts92 : Fin 92 → Nat := extend counts91 25
theorem counts92_eq : Table.fold (fun _ => 1) nodeCountAlgebra table92 = counts92 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table91 row91 counts91 25 counts91_eq (by decide +kernel)
def heights92 : Fin 92 → Nat := extend heights91 3
theorem heights92_eq : Table.fold (fun _ => 0) heightAlgebra table92 = heights92 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table91 row91 heights91 3 heights91_eq (by decide +kernel)
def row92 : Row 92 := Row.node (Kind.vector 1) (List.get ([⟨85, by decide⟩] : List (Fin 92)))
def table93 : Table 93 := .push table92 row92
def counts93 : Fin 93 → Nat := extend counts92 13
theorem counts93_eq : Table.fold (fun _ => 1) nodeCountAlgebra table93 = counts93 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table92 row92 counts92 13 counts92_eq (by decide +kernel)
def heights93 : Fin 93 → Nat := extend heights92 3
theorem heights93_eq : Table.fold (fun _ => 0) heightAlgebra table93 = heights93 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table92 row92 heights92 3 heights92_eq (by decide +kernel)
def row93 : Row 93 := Row.node (Kind.vector 2) (List.get ([⟨75, by decide⟩, ⟨83, by decide⟩] : List (Fin 93)))
def table94 : Table 94 := .push table93 row93
def counts94 : Fin 94 → Nat := extend counts93 25
theorem counts94_eq : Table.fold (fun _ => 1) nodeCountAlgebra table94 = counts94 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table93 row93 counts93 25 counts93_eq (by decide +kernel)
def heights94 : Fin 94 → Nat := extend heights93 3
theorem heights94_eq : Table.fold (fun _ => 0) heightAlgebra table94 = heights94 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table93 row93 heights93 3 heights93_eq (by decide +kernel)
def row94 : Row 94 := Row.node (Kind.map 3) (fun (slot : Fin 3 × Bool) => if slot.2 then (List.get ([⟨85, by decide⟩, ⟨45, by decide⟩, ⟨0, by decide⟩] : List (Fin 94))) slot.1 else (List.get ([⟨6, by decide⟩, ⟨11, by decide⟩, ⟨15, by decide⟩] : List (Fin 94))) slot.1)
def table95 : Table 95 := .push table94 row94
def counts95 : Fin 95 → Nat := extend counts94 18
theorem counts95_eq : Table.fold (fun _ => 1) nodeCountAlgebra table95 = counts95 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table94 row94 counts94 18 counts94_eq (by decide +kernel)
def heights95 : Fin 95 → Nat := extend heights94 3
theorem heights95_eq : Table.fold (fun _ => 0) heightAlgebra table95 = heights95 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table94 row94 heights94 3 heights94_eq (by decide +kernel)
def row95 : Row 95 := Row.node (Kind.vector 2) (List.get ([⟨79, by decide⟩, ⟨83, by decide⟩] : List (Fin 95)))
def table96 : Table 96 := .push table95 row95
def counts96 : Fin 96 → Nat := extend counts95 25
theorem counts96_eq : Table.fold (fun _ => 1) nodeCountAlgebra table96 = counts96 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table95 row95 counts95 25 counts95_eq (by decide +kernel)
def heights96 : Fin 96 → Nat := extend heights95 3
theorem heights96_eq : Table.fold (fun _ => 0) heightAlgebra table96 = heights96 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table95 row95 heights95 3 heights95_eq (by decide +kernel)
def row96 : Row 96 := Row.node (Kind.vector 3) (List.get ([⟨79, by decide⟩, ⟨82, by decide⟩, ⟨80, by decide⟩] : List (Fin 96)))
def table97 : Table 97 := .push table96 row96
def counts97 : Fin 97 → Nat := extend counts96 37
theorem counts97_eq : Table.fold (fun _ => 1) nodeCountAlgebra table97 = counts97 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table96 row96 counts96 37 counts96_eq (by decide +kernel)
def heights97 : Fin 97 → Nat := extend heights96 3
theorem heights97_eq : Table.fold (fun _ => 0) heightAlgebra table97 = heights97 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table96 row96 heights96 3 heights96_eq (by decide +kernel)
def row97 : Row 97 := Row.node (Kind.vector 2) (List.get ([⟨79, by decide⟩, ⟨77, by decide⟩] : List (Fin 97)))
def table98 : Table 98 := .push table97 row97
def counts98 : Fin 98 → Nat := extend counts97 25
theorem counts98_eq : Table.fold (fun _ => 1) nodeCountAlgebra table98 = counts98 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table97 row97 counts97 25 counts97_eq (by decide +kernel)
def heights98 : Fin 98 → Nat := extend heights97 3
theorem heights98_eq : Table.fold (fun _ => 0) heightAlgebra table98 = heights98 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table97 row97 heights97 3 heights97_eq (by decide +kernel)
def row98 : Row 98 := Row.node (Kind.vector 2) (List.get ([⟨75, by decide⟩, ⟨77, by decide⟩] : List (Fin 98)))
def table99 : Table 99 := .push table98 row98
def counts99 : Fin 99 → Nat := extend counts98 25
theorem counts99_eq : Table.fold (fun _ => 1) nodeCountAlgebra table99 = counts99 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table98 row98 counts98 25 counts98_eq (by decide +kernel)
def heights99 : Fin 99 → Nat := extend heights98 3
theorem heights99_eq : Table.fold (fun _ => 0) heightAlgebra table99 = heights99 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table98 row98 heights98 3 heights98_eq (by decide +kernel)
def row99 : Row 99 := Row.node (Kind.vector 2) (List.get ([⟨79, by decide⟩, ⟨76, by decide⟩] : List (Fin 99)))
def table100 : Table 100 := .push table99 row99
def counts100 : Fin 100 → Nat := extend counts99 25
theorem counts100_eq : Table.fold (fun _ => 1) nodeCountAlgebra table100 = counts100 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table99 row99 counts99 25 counts99_eq (by decide +kernel)
def heights100 : Fin 100 → Nat := extend heights99 3
theorem heights100_eq : Table.fold (fun _ => 0) heightAlgebra table100 = heights100 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table99 row99 heights99 3 heights99_eq (by decide +kernel)
def row100 : Row 100 := Row.node (Kind.vector 3) (List.get ([⟨83, by decide⟩, ⟨77, by decide⟩, ⟨76, by decide⟩] : List (Fin 100)))
def table101 : Table 101 := .push table100 row100
def counts101 : Fin 101 → Nat := extend counts100 37
theorem counts101_eq : Table.fold (fun _ => 1) nodeCountAlgebra table101 = counts101 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table100 row100 counts100 37 counts100_eq (by decide +kernel)
def heights101 : Fin 101 → Nat := extend heights100 3
theorem heights101_eq : Table.fold (fun _ => 0) heightAlgebra table101 = heights101 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table100 row100 heights100 3 heights100_eq (by decide +kernel)
def row101 : Row 101 := Row.node (Kind.vector 2) (List.get ([⟨83, by decide⟩, ⟨76, by decide⟩] : List (Fin 101)))
def table102 : Table 102 := .push table101 row101
def counts102 : Fin 102 → Nat := extend counts101 25
theorem counts102_eq : Table.fold (fun _ => 1) nodeCountAlgebra table102 = counts102 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table101 row101 counts101 25 counts101_eq (by decide +kernel)
def heights102 : Fin 102 → Nat := extend heights101 3
theorem heights102_eq : Table.fold (fun _ => 0) heightAlgebra table102 = heights102 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table101 row101 heights101 3 heights101_eq (by decide +kernel)
def row102 : Row 102 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨93, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 102))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 102))) slot.1)
def table103 : Table 103 := .push table102 row102
def counts103 : Fin 103 → Nat := extend counts102 36
theorem counts103_eq : Table.fold (fun _ => 1) nodeCountAlgebra table103 = counts103 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table102 row102 counts102 36 counts102_eq (by decide +kernel)
def heights103 : Fin 103 → Nat := extend heights102 4
theorem heights103_eq : Table.fold (fun _ => 0) heightAlgebra table103 = heights103 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table102 row102 heights102 4 heights102_eq (by decide +kernel)
def row103 : Row 103 := Row.node (Kind.vector 3) (List.get ([⟨100, by decide⟩, ⟨89, by decide⟩, ⟨96, by decide⟩] : List (Fin 103)))
def table104 : Table 104 := .push table103 row103
def counts104 : Fin 104 → Nat := extend counts103 112
theorem counts104_eq : Table.fold (fun _ => 1) nodeCountAlgebra table104 = counts104 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table103 row103 counts103 112 counts103_eq (by decide +kernel)
def heights104 : Fin 104 → Nat := extend heights103 4
theorem heights104_eq : Table.fold (fun _ => 0) heightAlgebra table104 = heights104 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table103 row103 heights103 4 heights103_eq (by decide +kernel)
def row104 : Row 104 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨91, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 104))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 104))) slot.1)
def table105 : Table 105 := .push table104 row104
def counts105 : Fin 105 → Nat := extend counts104 36
theorem counts105_eq : Table.fold (fun _ => 1) nodeCountAlgebra table105 = counts105 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table104 row104 counts104 36 counts104_eq (by decide +kernel)
def heights105 : Fin 105 → Nat := extend heights104 4
theorem heights105_eq : Table.fold (fun _ => 0) heightAlgebra table105 = heights105 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table104 row104 heights104 4 heights104_eq (by decide +kernel)
def row105 : Row 105 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨92, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 105))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 105))) slot.1)
def table106 : Table 106 := .push table105 row105
def counts106 : Fin 106 → Nat := extend counts105 24
theorem counts106_eq : Table.fold (fun _ => 1) nodeCountAlgebra table106 = counts106 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table105 row105 counts105 24 counts105_eq (by decide +kernel)
def heights106 : Fin 106 → Nat := extend heights105 4
theorem heights106_eq : Table.fold (fun _ => 0) heightAlgebra table106 = heights106 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table105 row105 heights105 4 heights105_eq (by decide +kernel)
def row106 : Row 106 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨88, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 106))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 106))) slot.1)
def table107 : Table 107 := .push table106 row106
def counts107 : Fin 107 → Nat := extend counts106 36
theorem counts107_eq : Table.fold (fun _ => 1) nodeCountAlgebra table107 = counts107 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table106 row106 counts106 36 counts106_eq (by decide +kernel)
def heights107 : Fin 107 → Nat := extend heights106 4
theorem heights107_eq : Table.fold (fun _ => 0) heightAlgebra table107 = heights107 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table106 row106 heights106 4 heights106_eq (by decide +kernel)
def row107 : Row 107 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨95, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 107))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 107))) slot.1)
def table108 : Table 108 := .push table107 row107
def counts108 : Fin 108 → Nat := extend counts107 36
theorem counts108_eq : Table.fold (fun _ => 1) nodeCountAlgebra table108 = counts108 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table107 row107 counts107 36 counts107_eq (by decide +kernel)
def heights108 : Fin 108 → Nat := extend heights107 4
theorem heights108_eq : Table.fold (fun _ => 0) heightAlgebra table108 = heights108 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table107 row107 heights107 4 heights107_eq (by decide +kernel)
def row108 : Row 108 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨99, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 108))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 108))) slot.1)
def table109 : Table 109 := .push table108 row108
def counts109 : Fin 109 → Nat := extend counts108 36
theorem counts109_eq : Table.fold (fun _ => 1) nodeCountAlgebra table109 = counts109 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table108 row108 counts108 36 counts108_eq (by decide +kernel)
def heights109 : Fin 109 → Nat := extend heights108 4
theorem heights109_eq : Table.fold (fun _ => 0) heightAlgebra table109 = heights109 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table108 row108 heights108 4 heights108_eq (by decide +kernel)
def row109 : Row 109 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨90, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 109))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 109))) slot.1)
def table110 : Table 110 := .push table109 row109
def counts110 : Fin 110 → Nat := extend counts109 36
theorem counts110_eq : Table.fold (fun _ => 1) nodeCountAlgebra table110 = counts110 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table109 row109 counts109 36 counts109_eq (by decide +kernel)
def heights110 : Fin 110 → Nat := extend heights109 4
theorem heights110_eq : Table.fold (fun _ => 0) heightAlgebra table110 = heights110 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table109 row109 heights109 4 heights109_eq (by decide +kernel)
def row110 : Row 110 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨98, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 110))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 110))) slot.1)
def table111 : Table 111 := .push table110 row110
def counts111 : Fin 111 → Nat := extend counts110 36
theorem counts111_eq : Table.fold (fun _ => 1) nodeCountAlgebra table111 = counts111 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table110 row110 counts110 36 counts110_eq (by decide +kernel)
def heights111 : Fin 111 → Nat := extend heights110 4
theorem heights111_eq : Table.fold (fun _ => 0) heightAlgebra table111 = heights111 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table110 row110 heights110 4 heights110_eq (by decide +kernel)
def row111 : Row 111 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨97, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 111))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 111))) slot.1)
def table112 : Table 112 := .push table111 row111
def counts112 : Fin 112 → Nat := extend counts111 36
theorem counts112_eq : Table.fold (fun _ => 1) nodeCountAlgebra table112 = counts112 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table111 row111 counts111 36 counts111_eq (by decide +kernel)
def heights112 : Fin 112 → Nat := extend heights111 4
theorem heights112_eq : Table.fold (fun _ => 0) heightAlgebra table112 = heights112 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table111 row111 heights111 4 heights111_eq (by decide +kernel)
def row112 : Row 112 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨101, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 112))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 112))) slot.1)
def table113 : Table 113 := .push table112 row112
def counts113 : Fin 113 → Nat := extend counts112 36
theorem counts113_eq : Table.fold (fun _ => 1) nodeCountAlgebra table113 = counts113 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table112 row112 counts112 36 counts112_eq (by decide +kernel)
def heights113 : Fin 113 → Nat := extend heights112 4
theorem heights113_eq : Table.fold (fun _ => 0) heightAlgebra table113 = heights113 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table112 row112 heights112 4 heights112_eq (by decide +kernel)
def row113 : Row 113 := Row.node (Kind.vector 2) (List.get ([⟨82, by decide⟩, ⟨111, by decide⟩] : List (Fin 113)))
def table114 : Table 114 := .push table113 row113
def counts114 : Fin 114 → Nat := extend counts113 49
theorem counts114_eq : Table.fold (fun _ => 1) nodeCountAlgebra table114 = counts114 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table113 row113 counts113 49 counts113_eq (by decide +kernel)
def heights114 : Fin 114 → Nat := extend heights113 5
theorem heights114_eq : Table.fold (fun _ => 0) heightAlgebra table114 = heights114 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table113 row113 heights113 5 heights113_eq (by decide +kernel)
def row114 : Row 114 := Row.node (Kind.vector 2) (List.get ([⟨76, by decide⟩, ⟨112, by decide⟩] : List (Fin 114)))
def table115 : Table 115 := .push table114 row114
def counts115 : Fin 115 → Nat := extend counts114 49
theorem counts115_eq : Table.fold (fun _ => 1) nodeCountAlgebra table115 = counts115 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table114 row114 counts114 49 counts114_eq (by decide +kernel)
def heights115 : Fin 115 → Nat := extend heights114 5
theorem heights115_eq : Table.fold (fun _ => 0) heightAlgebra table115 = heights115 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table114 row114 heights114 5 heights114_eq (by decide +kernel)
def row115 : Row 115 := Row.node (Kind.vector 2) (List.get ([⟨83, by decide⟩, ⟨104, by decide⟩] : List (Fin 115)))
def table116 : Table 116 := .push table115 row115
def counts116 : Fin 116 → Nat := extend counts115 49
theorem counts116_eq : Table.fold (fun _ => 1) nodeCountAlgebra table116 = counts116 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table115 row115 counts115 49 counts115_eq (by decide +kernel)
def heights116 : Fin 116 → Nat := extend heights115 5
theorem heights116_eq : Table.fold (fun _ => 0) heightAlgebra table116 = heights116 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table115 row115 heights115 5 heights115_eq (by decide +kernel)
def row116 : Row 116 := Row.node (Kind.vector 1) (List.get ([⟨105, by decide⟩] : List (Fin 116)))
def table117 : Table 117 := .push table116 row116
def counts117 : Fin 117 → Nat := extend counts116 25
theorem counts117_eq : Table.fold (fun _ => 1) nodeCountAlgebra table117 = counts117 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table116 row116 counts116 25 counts116_eq (by decide +kernel)
def heights117 : Fin 117 → Nat := extend heights116 5
theorem heights117_eq : Table.fold (fun _ => 0) heightAlgebra table117 = heights117 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table116 row116 heights116 5 heights116_eq (by decide +kernel)
def row117 : Row 117 := Row.node (Kind.vector 2) (List.get ([⟨75, by decide⟩, ⟨102, by decide⟩] : List (Fin 117)))
def table118 : Table 118 := .push table117 row117
def counts118 : Fin 118 → Nat := extend counts117 49
theorem counts118_eq : Table.fold (fun _ => 1) nodeCountAlgebra table118 = counts118 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table117 row117 counts117 49 counts117_eq (by decide +kernel)
def heights118 : Fin 118 → Nat := extend heights117 5
theorem heights118_eq : Table.fold (fun _ => 0) heightAlgebra table118 = heights118 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table117 row117 heights117 5 heights117_eq (by decide +kernel)
def row118 : Row 118 := Row.node (Kind.vector 2) (List.get ([⟨87, by decide⟩, ⟨109, by decide⟩] : List (Fin 118)))
def table119 : Table 119 := .push table118 row118
def counts119 : Fin 119 → Nat := extend counts118 49
theorem counts119_eq : Table.fold (fun _ => 1) nodeCountAlgebra table119 = counts119 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table118 row118 counts118 49 counts118_eq (by decide +kernel)
def heights119 : Fin 119 → Nat := extend heights118 5
theorem heights119_eq : Table.fold (fun _ => 0) heightAlgebra table119 = heights119 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table118 row118 heights118 5 heights118_eq (by decide +kernel)
def row119 : Row 119 := Row.node (Kind.map 1) (fun (slot : Fin 1 × Bool) => if slot.2 then (List.get ([⟨103, by decide⟩] : List (Fin 119))) slot.1 else (List.get ([⟨63, by decide⟩] : List (Fin 119))) slot.1)
def table120 : Table 120 := .push table119 row119
def counts120 : Fin 120 → Nat := extend counts119 114
theorem counts120_eq : Table.fold (fun _ => 1) nodeCountAlgebra table120 = counts120 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table119 row119 counts119 114 counts119_eq (by decide +kernel)
def heights120 : Fin 120 → Nat := extend heights119 5
theorem heights120_eq : Table.fold (fun _ => 0) heightAlgebra table120 = heights120 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table119 row119 heights119 5 heights119_eq (by decide +kernel)
def row120 : Row 120 := Row.node (Kind.vector 2) (List.get ([⟨77, by decide⟩, ⟨106, by decide⟩] : List (Fin 120)))
def table121 : Table 121 := .push table120 row120
def counts121 : Fin 121 → Nat := extend counts120 49
theorem counts121_eq : Table.fold (fun _ => 1) nodeCountAlgebra table121 = counts121 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table120 row120 counts120 49 counts120_eq (by decide +kernel)
def heights121 : Fin 121 → Nat := extend heights120 5
theorem heights121_eq : Table.fold (fun _ => 0) heightAlgebra table121 = heights121 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table120 row120 heights120 5 heights120_eq (by decide +kernel)
def row121 : Row 121 := Row.node (Kind.vector 2) (List.get ([⟨79, by decide⟩, ⟨107, by decide⟩] : List (Fin 121)))
def table122 : Table 122 := .push table121 row121
def counts122 : Fin 122 → Nat := extend counts121 49
theorem counts122_eq : Table.fold (fun _ => 1) nodeCountAlgebra table122 = counts122 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table121 row121 counts121 49 counts121_eq (by decide +kernel)
def heights122 : Fin 122 → Nat := extend heights121 5
theorem heights122_eq : Table.fold (fun _ => 0) heightAlgebra table122 = heights122 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table121 row121 heights121 5 heights121_eq (by decide +kernel)
def row122 : Row 122 := Row.node (Kind.vector 2) (List.get ([⟨81, by decide⟩, ⟨110, by decide⟩] : List (Fin 122)))
def table123 : Table 123 := .push table122 row122
def counts123 : Fin 123 → Nat := extend counts122 49
theorem counts123_eq : Table.fold (fun _ => 1) nodeCountAlgebra table123 = counts123 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table122 row122 counts122 49 counts122_eq (by decide +kernel)
def heights123 : Fin 123 → Nat := extend heights122 5
theorem heights123_eq : Table.fold (fun _ => 0) heightAlgebra table123 = heights123 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table122 row122 heights122 5 heights122_eq (by decide +kernel)
def row123 : Row 123 := Row.node (Kind.vector 2) (List.get ([⟨80, by decide⟩, ⟨108, by decide⟩] : List (Fin 123)))
def table124 : Table 124 := .push table123 row123
def counts124 : Fin 124 → Nat := extend counts123 49
theorem counts124_eq : Table.fold (fun _ => 1) nodeCountAlgebra table124 = counts124 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table123 row123 counts123 49 counts123_eq (by decide +kernel)
def heights124 : Fin 124 → Nat := extend heights123 5
theorem heights124_eq : Table.fold (fun _ => 0) heightAlgebra table124 = heights124 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table123 row123 heights123 5 heights123_eq (by decide +kernel)
def row124 : Row 124 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨117, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 124))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 124))) slot.1)
def table125 : Table 125 := .push table124 row124
def counts125 : Fin 125 → Nat := extend counts124 60
theorem counts125_eq : Table.fold (fun _ => 1) nodeCountAlgebra table125 = counts125 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table124 row124 counts124 60 counts124_eq (by decide +kernel)
def heights125 : Fin 125 → Nat := extend heights124 6
theorem heights125_eq : Table.fold (fun _ => 0) heightAlgebra table125 = heights125 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table124 row124 heights124 6 heights124_eq (by decide +kernel)
def row125 : Row 125 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨115, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 125))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 125))) slot.1)
def table126 : Table 126 := .push table125 row125
def counts126 : Fin 126 → Nat := extend counts125 60
theorem counts126_eq : Table.fold (fun _ => 1) nodeCountAlgebra table126 = counts126 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table125 row125 counts125 60 counts125_eq (by decide +kernel)
def heights126 : Fin 126 → Nat := extend heights125 6
theorem heights126_eq : Table.fold (fun _ => 0) heightAlgebra table126 = heights126 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table125 row125 heights125 6 heights125_eq (by decide +kernel)
def row126 : Row 126 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨118, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 126))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 126))) slot.1)
def table127 : Table 127 := .push table126 row126
def counts127 : Fin 127 → Nat := extend counts126 60
theorem counts127_eq : Table.fold (fun _ => 1) nodeCountAlgebra table127 = counts127 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table126 row126 counts126 60 counts126_eq (by decide +kernel)
def heights127 : Fin 127 → Nat := extend heights126 6
theorem heights127_eq : Table.fold (fun _ => 0) heightAlgebra table127 = heights127 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table126 row126 heights126 6 heights126_eq (by decide +kernel)
def row127 : Row 127 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨114, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 127))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 127))) slot.1)
def table128 : Table 128 := .push table127 row127
def counts128 : Fin 128 → Nat := extend counts127 60
theorem counts128_eq : Table.fold (fun _ => 1) nodeCountAlgebra table128 = counts128 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table127 row127 counts127 60 counts127_eq (by decide +kernel)
def heights128 : Fin 128 → Nat := extend heights127 6
theorem heights128_eq : Table.fold (fun _ => 0) heightAlgebra table128 = heights128 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table127 row127 heights127 6 heights127_eq (by decide +kernel)
def row128 : Row 128 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨122, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 128))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 128))) slot.1)
def table129 : Table 129 := .push table128 row128
def counts129 : Fin 129 → Nat := extend counts128 60
theorem counts129_eq : Table.fold (fun _ => 1) nodeCountAlgebra table129 = counts129 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table128 row128 counts128 60 counts128_eq (by decide +kernel)
def heights129 : Fin 129 → Nat := extend heights128 6
theorem heights129_eq : Table.fold (fun _ => 0) heightAlgebra table129 = heights129 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table128 row128 heights128 6 heights128_eq (by decide +kernel)
def row129 : Row 129 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨121, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 129))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 129))) slot.1)
def table130 : Table 130 := .push table129 row129
def counts130 : Fin 130 → Nat := extend counts129 60
theorem counts130_eq : Table.fold (fun _ => 1) nodeCountAlgebra table130 = counts130 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table129 row129 counts129 60 counts129_eq (by decide +kernel)
def heights130 : Fin 130 → Nat := extend heights129 6
theorem heights130_eq : Table.fold (fun _ => 0) heightAlgebra table130 = heights130 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table129 row129 heights129 6 heights129_eq (by decide +kernel)
def row130 : Row 130 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨123, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 130))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 130))) slot.1)
def table131 : Table 131 := .push table130 row130
def counts131 : Fin 131 → Nat := extend counts130 60
theorem counts131_eq : Table.fold (fun _ => 1) nodeCountAlgebra table131 = counts131 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table130 row130 counts130 60 counts130_eq (by decide +kernel)
def heights131 : Fin 131 → Nat := extend heights130 6
theorem heights131_eq : Table.fold (fun _ => 0) heightAlgebra table131 = heights131 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table130 row130 heights130 6 heights130_eq (by decide +kernel)
def row131 : Row 131 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨113, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 131))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 131))) slot.1)
def table132 : Table 132 := .push table131 row131
def counts132 : Fin 132 → Nat := extend counts131 60
theorem counts132_eq : Table.fold (fun _ => 1) nodeCountAlgebra table132 = counts132 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table131 row131 counts131 60 counts131_eq (by decide +kernel)
def heights132 : Fin 132 → Nat := extend heights131 6
theorem heights132_eq : Table.fold (fun _ => 0) heightAlgebra table132 = heights132 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table131 row131 heights131 6 heights131_eq (by decide +kernel)
def row132 : Row 132 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨116, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 132))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 132))) slot.1)
def table133 : Table 133 := .push table132 row132
def counts133 : Fin 133 → Nat := extend counts132 36
theorem counts133_eq : Table.fold (fun _ => 1) nodeCountAlgebra table133 = counts133 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table132 row132 counts132 36 counts132_eq (by decide +kernel)
def heights133 : Fin 133 → Nat := extend heights132 6
theorem heights133_eq : Table.fold (fun _ => 0) heightAlgebra table133 = heights133 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table132 row132 heights132 6 heights132_eq (by decide +kernel)
def row133 : Row 133 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨120, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 133))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 133))) slot.1)
def table134 : Table 134 := .push table133 row133
def counts134 : Fin 134 → Nat := extend counts133 60
theorem counts134_eq : Table.fold (fun _ => 1) nodeCountAlgebra table134 = counts134 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table133 row133 counts133 60 counts133_eq (by decide +kernel)
def heights134 : Fin 134 → Nat := extend heights133 6
theorem heights134_eq : Table.fold (fun _ => 0) heightAlgebra table134 = heights134 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table133 row133 heights133 6 heights133_eq (by decide +kernel)
def row134 : Row 134 := Row.node (Kind.map 8) (fun (slot : Fin 8 × Bool) => if slot.2 then (List.get ([⟨119, by decide⟩, ⟨35, by decide⟩, ⟨14, by decide⟩, ⟨78, by decide⟩, ⟨48, by decide⟩, ⟨86, by decide⟩, ⟨85, by decide⟩, ⟨85, by decide⟩] : List (Fin 134))) slot.1 else (List.get ([⟨5, by decide⟩, ⟨7, by decide⟩, ⟨36, by decide⟩, ⟨39, by decide⟩, ⟨40, by decide⟩, ⟨43, by decide⟩, ⟨52, by decide⟩, ⟨53, by decide⟩] : List (Fin 134))) slot.1)
def table135 : Table 135 := .push table134 row134
def counts135 : Fin 135 → Nat := extend counts134 168
theorem counts135_eq : Table.fold (fun _ => 1) nodeCountAlgebra table135 = counts135 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table134 row134 counts134 168 counts134_eq (by decide +kernel)
def heights135 : Fin 135 → Nat := extend heights134 6
theorem heights135_eq : Table.fold (fun _ => 0) heightAlgebra table135 = heights135 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table134 row134 heights134 6 heights134_eq (by decide +kernel)
def row135 : Row 135 := Row.node (Kind.vector 2) (List.get ([⟨131, by decide⟩, ⟨128, by decide⟩] : List (Fin 135)))
def table136 : Table 136 := .push table135 row135
def counts136 : Fin 136 → Nat := extend counts135 121
theorem counts136_eq : Table.fold (fun _ => 1) nodeCountAlgebra table136 = counts136 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table135 row135 counts135 121 counts135_eq (by decide +kernel)
def heights136 : Fin 136 → Nat := extend heights135 7
theorem heights136_eq : Table.fold (fun _ => 0) heightAlgebra table136 = heights136 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table135 row135 heights135 7 heights135_eq (by decide +kernel)
def row136 : Row 136 := Row.node (Kind.vector 2) (List.get ([⟨133, by decide⟩, ⟨128, by decide⟩] : List (Fin 136)))
def table137 : Table 137 := .push table136 row136
def counts137 : Fin 137 → Nat := extend counts136 121
theorem counts137_eq : Table.fold (fun _ => 1) nodeCountAlgebra table137 = counts137 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table136 row136 counts136 121 counts136_eq (by decide +kernel)
def heights137 : Fin 137 → Nat := extend heights136 7
theorem heights137_eq : Table.fold (fun _ => 0) heightAlgebra table137 = heights137 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table136 row136 heights136 7 heights136_eq (by decide +kernel)
def row137 : Row 137 := Row.node (Kind.vector 2) (List.get ([⟨131, by decide⟩, ⟨126, by decide⟩] : List (Fin 137)))
def table138 : Table 138 := .push table137 row137
def counts138 : Fin 138 → Nat := extend counts137 121
theorem counts138_eq : Table.fold (fun _ => 1) nodeCountAlgebra table138 = counts138 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table137 row137 counts137 121 counts137_eq (by decide +kernel)
def heights138 : Fin 138 → Nat := extend heights137 7
theorem heights138_eq : Table.fold (fun _ => 0) heightAlgebra table138 = heights138 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table137 row137 heights137 7 heights137_eq (by decide +kernel)
def row138 : Row 138 := Row.node (Kind.map 3) (fun (slot : Fin 3 × Bool) => if slot.2 then (List.get ([⟨132, by decide⟩, ⟨45, by decide⟩, ⟨61, by decide⟩] : List (Fin 138))) slot.1 else (List.get ([⟨6, by decide⟩, ⟨11, by decide⟩, ⟨15, by decide⟩] : List (Fin 138))) slot.1)
def table139 : Table 139 := .push table138 row138
def counts139 : Fin 139 → Nat := extend counts138 42
theorem counts139_eq : Table.fold (fun _ => 1) nodeCountAlgebra table139 = counts139 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table138 row138 counts138 42 counts138_eq (by decide +kernel)
def heights139 : Fin 139 → Nat := extend heights138 7
theorem heights139_eq : Table.fold (fun _ => 0) heightAlgebra table139 = heights139 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table138 row138 heights138 7 heights138_eq (by decide +kernel)
def row139 : Row 139 := Row.node (Kind.vector 2) (List.get ([⟨133, by decide⟩, ⟨124, by decide⟩] : List (Fin 139)))
def table140 : Table 140 := .push table139 row139
def counts140 : Fin 140 → Nat := extend counts139 121
theorem counts140_eq : Table.fold (fun _ => 1) nodeCountAlgebra table140 = counts140 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table139 row139 counts139 121 counts139_eq (by decide +kernel)
def heights140 : Fin 140 → Nat := extend heights139 7
theorem heights140_eq : Table.fold (fun _ => 0) heightAlgebra table140 = heights140 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table139 row139 heights139 7 heights139_eq (by decide +kernel)
def row140 : Row 140 := Row.node (Kind.vector 2) (List.get ([⟨131, by decide⟩, ⟨124, by decide⟩] : List (Fin 140)))
def table141 : Table 141 := .push table140 row140
def counts141 : Fin 141 → Nat := extend counts140 121
theorem counts141_eq : Table.fold (fun _ => 1) nodeCountAlgebra table141 = counts141 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table140 row140 counts140 121 counts140_eq (by decide +kernel)
def heights141 : Fin 141 → Nat := extend heights140 7
theorem heights141_eq : Table.fold (fun _ => 0) heightAlgebra table141 = heights141 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table140 row140 heights140 7 heights140_eq (by decide +kernel)
def row141 : Row 141 := Row.node (Kind.vector 2) (List.get ([⟨128, by decide⟩, ⟨124, by decide⟩] : List (Fin 141)))
def table142 : Table 142 := .push table141 row141
def counts142 : Fin 142 → Nat := extend counts141 121
theorem counts142_eq : Table.fold (fun _ => 1) nodeCountAlgebra table142 = counts142 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table141 row141 counts141 121 counts141_eq (by decide +kernel)
def heights142 : Fin 142 → Nat := extend heights141 7
theorem heights142_eq : Table.fold (fun _ => 0) heightAlgebra table142 = heights142 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table141 row141 heights141 7 heights141_eq (by decide +kernel)
def row142 : Row 142 := Row.node (Kind.vector 2) (List.get ([⟨128, by decide⟩, ⟨128, by decide⟩] : List (Fin 142)))
def table143 : Table 143 := .push table142 row142
def counts143 : Fin 143 → Nat := extend counts142 121
theorem counts143_eq : Table.fold (fun _ => 1) nodeCountAlgebra table143 = counts143 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table142 row142 counts142 121 counts142_eq (by decide +kernel)
def heights143 : Fin 143 → Nat := extend heights142 7
theorem heights143_eq : Table.fold (fun _ => 0) heightAlgebra table143 = heights143 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table142 row142 heights142 7 heights142_eq (by decide +kernel)
def row143 : Row 143 := Row.node (Kind.vector 2) (List.get ([⟨128, by decide⟩, ⟨126, by decide⟩] : List (Fin 143)))
def table144 : Table 144 := .push table143 row143
def counts144 : Fin 144 → Nat := extend counts143 121
theorem counts144_eq : Table.fold (fun _ => 1) nodeCountAlgebra table144 = counts144 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table143 row143 counts143 121 counts143_eq (by decide +kernel)
def heights144 : Fin 144 → Nat := extend heights143 7
theorem heights144_eq : Table.fold (fun _ => 0) heightAlgebra table144 = heights144 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table143 row143 heights143 7 heights143_eq (by decide +kernel)
def row144 : Row 144 := Row.node (Kind.vector 2) (List.get ([⟨133, by decide⟩, ⟨126, by decide⟩] : List (Fin 144)))
def table145 : Table 145 := .push table144 row144
def counts145 : Fin 145 → Nat := extend counts144 121
theorem counts145_eq : Table.fold (fun _ => 1) nodeCountAlgebra table145 = counts145 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table144 row144 counts144 121 counts144_eq (by decide +kernel)
def heights145 : Fin 145 → Nat := extend heights144 7
theorem heights145_eq : Table.fold (fun _ => 0) heightAlgebra table145 = heights145 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table144 row144 heights144 7 heights144_eq (by decide +kernel)
def row145 : Row 145 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨139, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 145))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 145))) slot.1)
def table146 : Table 146 := .push table145 row145
def counts146 : Fin 146 → Nat := extend counts145 132
theorem counts146_eq : Table.fold (fun _ => 1) nodeCountAlgebra table146 = counts146 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table145 row145 counts145 132 counts145_eq (by decide +kernel)
def heights146 : Fin 146 → Nat := extend heights145 8
theorem heights146_eq : Table.fold (fun _ => 0) heightAlgebra table146 = heights146 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table145 row145 heights145 8 heights145_eq (by decide +kernel)
def row146 : Row 146 := Row.node (Kind.vector 2) (List.get ([⟨138, by decide⟩, ⟨94, by decide⟩] : List (Fin 146)))
def table147 : Table 147 := .push table146 row146
def counts147 : Fin 147 → Nat := extend counts146 61
theorem counts147_eq : Table.fold (fun _ => 1) nodeCountAlgebra table147 = counts147 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table146 row146 counts146 61 counts146_eq (by decide +kernel)
def heights147 : Fin 147 → Nat := extend heights146 8
theorem heights147_eq : Table.fold (fun _ => 0) heightAlgebra table147 = heights147 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table146 row146 heights146 8 heights146_eq (by decide +kernel)
def row147 : Row 147 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨143, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 147))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 147))) slot.1)
def table148 : Table 148 := .push table147 row147
def counts148 : Fin 148 → Nat := extend counts147 132
theorem counts148_eq : Table.fold (fun _ => 1) nodeCountAlgebra table148 = counts148 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table147 row147 counts147 132 counts147_eq (by decide +kernel)
def heights148 : Fin 148 → Nat := extend heights147 8
theorem heights148_eq : Table.fold (fun _ => 0) heightAlgebra table148 = heights148 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table147 row147 heights147 8 heights147_eq (by decide +kernel)
def row148 : Row 148 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨136, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 148))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 148))) slot.1)
def table149 : Table 149 := .push table148 row148
def counts149 : Fin 149 → Nat := extend counts148 132
theorem counts149_eq : Table.fold (fun _ => 1) nodeCountAlgebra table149 = counts149 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table148 row148 counts148 132 counts148_eq (by decide +kernel)
def heights149 : Fin 149 → Nat := extend heights148 8
theorem heights149_eq : Table.fold (fun _ => 0) heightAlgebra table149 = heights149 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table148 row148 heights148 8 heights148_eq (by decide +kernel)
def row149 : Row 149 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨141, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 149))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 149))) slot.1)
def table150 : Table 150 := .push table149 row149
def counts150 : Fin 150 → Nat := extend counts149 132
theorem counts150_eq : Table.fold (fun _ => 1) nodeCountAlgebra table150 = counts150 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table149 row149 counts149 132 counts149_eq (by decide +kernel)
def heights150 : Fin 150 → Nat := extend heights149 8
theorem heights150_eq : Table.fold (fun _ => 0) heightAlgebra table150 = heights150 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table149 row149 heights149 8 heights149_eq (by decide +kernel)
def row150 : Row 150 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨144, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 150))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 150))) slot.1)
def table151 : Table 151 := .push table150 row150
def counts151 : Fin 151 → Nat := extend counts150 132
theorem counts151_eq : Table.fold (fun _ => 1) nodeCountAlgebra table151 = counts151 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table150 row150 counts150 132 counts150_eq (by decide +kernel)
def heights151 : Fin 151 → Nat := extend heights150 8
theorem heights151_eq : Table.fold (fun _ => 0) heightAlgebra table151 = heights151 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table150 row150 heights150 8 heights150_eq (by decide +kernel)
def row151 : Row 151 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨142, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 151))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 151))) slot.1)
def table152 : Table 152 := .push table151 row151
def counts152 : Fin 152 → Nat := extend counts151 132
theorem counts152_eq : Table.fold (fun _ => 1) nodeCountAlgebra table152 = counts152 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table151 row151 counts151 132 counts151_eq (by decide +kernel)
def heights152 : Fin 152 → Nat := extend heights151 8
theorem heights152_eq : Table.fold (fun _ => 0) heightAlgebra table152 = heights152 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table151 row151 heights151 8 heights151_eq (by decide +kernel)
def row152 : Row 152 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨135, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 152))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 152))) slot.1)
def table153 : Table 153 := .push table152 row152
def counts153 : Fin 153 → Nat := extend counts152 132
theorem counts153_eq : Table.fold (fun _ => 1) nodeCountAlgebra table153 = counts153 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table152 row152 counts152 132 counts152_eq (by decide +kernel)
def heights153 : Fin 153 → Nat := extend heights152 8
theorem heights153_eq : Table.fold (fun _ => 0) heightAlgebra table153 = heights153 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table152 row152 heights152 8 heights152_eq (by decide +kernel)
def row153 : Row 153 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨137, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 153))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 153))) slot.1)
def table154 : Table 154 := .push table153 row153
def counts154 : Fin 154 → Nat := extend counts153 132
theorem counts154_eq : Table.fold (fun _ => 1) nodeCountAlgebra table154 = counts154 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table153 row153 counts153 132 counts153_eq (by decide +kernel)
def heights154 : Fin 154 → Nat := extend heights153 8
theorem heights154_eq : Table.fold (fun _ => 0) heightAlgebra table154 = heights154 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table153 row153 heights153 8 heights153_eq (by decide +kernel)
def row154 : Row 154 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨140, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 154))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 154))) slot.1)
def table155 : Table 155 := .push table154 row154
def counts155 : Fin 155 → Nat := extend counts154 132
theorem counts155_eq : Table.fold (fun _ => 1) nodeCountAlgebra table155 = counts155 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table154 row154 counts154 132 counts154_eq (by decide +kernel)
def heights155 : Fin 155 → Nat := extend heights154 8
theorem heights155_eq : Table.fold (fun _ => 0) heightAlgebra table155 = heights155 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table154 row154 heights154 8 heights154_eq (by decide +kernel)
def row155 : Row 155 := Row.node (Kind.vector 2) (List.get ([⟨130, by decide⟩, ⟨153, by decide⟩] : List (Fin 155)))
def table156 : Table 156 := .push table155 row155
def counts156 : Fin 156 → Nat := extend counts155 193
theorem counts156_eq : Table.fold (fun _ => 1) nodeCountAlgebra table156 = counts156 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table155 row155 counts155 193 counts155_eq (by decide +kernel)
def heights156 : Fin 156 → Nat := extend heights155 9
theorem heights156_eq : Table.fold (fun _ => 0) heightAlgebra table156 = heights156 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table155 row155 heights155 9 heights155_eq (by decide +kernel)
def row156 : Row 156 := Row.node (Kind.vector 2) (List.get ([⟨128, by decide⟩, ⟨151, by decide⟩] : List (Fin 156)))
def table157 : Table 157 := .push table156 row156
def counts157 : Fin 157 → Nat := extend counts156 193
theorem counts157_eq : Table.fold (fun _ => 1) nodeCountAlgebra table157 = counts157 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table156 row156 counts156 193 counts156_eq (by decide +kernel)
def heights157 : Fin 157 → Nat := extend heights156 9
theorem heights157_eq : Table.fold (fun _ => 0) heightAlgebra table157 = heights157 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table156 row156 heights156 9 heights156_eq (by decide +kernel)
def row157 : Row 157 := Row.node (Kind.vector 2) (List.get ([⟨127, by decide⟩, ⟨150, by decide⟩] : List (Fin 157)))
def table158 : Table 158 := .push table157 row157
def counts158 : Fin 158 → Nat := extend counts157 193
theorem counts158_eq : Table.fold (fun _ => 1) nodeCountAlgebra table158 = counts158 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table157 row157 counts157 193 counts157_eq (by decide +kernel)
def heights158 : Fin 158 → Nat := extend heights157 9
theorem heights158_eq : Table.fold (fun _ => 0) heightAlgebra table158 = heights158 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table157 row157 heights157 9 heights157_eq (by decide +kernel)
def row158 : Row 158 := Row.node (Kind.vector 2) (List.get ([⟨124, by decide⟩, ⟨149, by decide⟩] : List (Fin 158)))
def table159 : Table 159 := .push table158 row158
def counts159 : Fin 159 → Nat := extend counts158 193
theorem counts159_eq : Table.fold (fun _ => 1) nodeCountAlgebra table159 = counts159 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table158 row158 counts158 193 counts158_eq (by decide +kernel)
def heights159 : Fin 159 → Nat := extend heights158 9
theorem heights159_eq : Table.fold (fun _ => 0) heightAlgebra table159 = heights159 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table158 row158 heights158 9 heights158_eq (by decide +kernel)
def row159 : Row 159 := Row.node (Kind.vector 2) (List.get ([⟨125, by decide⟩, ⟨145, by decide⟩] : List (Fin 159)))
def table160 : Table 160 := .push table159 row159
def counts160 : Fin 160 → Nat := extend counts159 193
theorem counts160_eq : Table.fold (fun _ => 1) nodeCountAlgebra table160 = counts160 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table159 row159 counts159 193 counts159_eq (by decide +kernel)
def heights160 : Fin 160 → Nat := extend heights159 9
theorem heights160_eq : Table.fold (fun _ => 0) heightAlgebra table160 = heights160 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table159 row159 heights159 9 heights159_eq (by decide +kernel)
def row160 : Row 160 := Row.node (Kind.vector 2) (List.get ([⟨133, by decide⟩, ⟨148, by decide⟩] : List (Fin 160)))
def table161 : Table 161 := .push table160 row160
def counts161 : Fin 161 → Nat := extend counts160 193
theorem counts161_eq : Table.fold (fun _ => 1) nodeCountAlgebra table161 = counts161 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table160 row160 counts160 193 counts160_eq (by decide +kernel)
def heights161 : Fin 161 → Nat := extend heights160 9
theorem heights161_eq : Table.fold (fun _ => 0) heightAlgebra table161 = heights161 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table160 row160 heights160 9 heights160_eq (by decide +kernel)
def row161 : Row 161 := Row.node (Kind.vector 2) (List.get ([⟨131, by decide⟩, ⟨152, by decide⟩] : List (Fin 161)))
def table162 : Table 162 := .push table161 row161
def counts162 : Fin 162 → Nat := extend counts161 193
theorem counts162_eq : Table.fold (fun _ => 1) nodeCountAlgebra table162 = counts162 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table161 row161 counts161 193 counts161_eq (by decide +kernel)
def heights162 : Fin 162 → Nat := extend heights161 9
theorem heights162_eq : Table.fold (fun _ => 0) heightAlgebra table162 = heights162 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table161 row161 heights161 9 heights161_eq (by decide +kernel)
def row162 : Row 162 := Row.node (Kind.vector 2) (List.get ([⟨129, by decide⟩, ⟨154, by decide⟩] : List (Fin 162)))
def table163 : Table 163 := .push table162 row162
def counts163 : Fin 163 → Nat := extend counts162 193
theorem counts163_eq : Table.fold (fun _ => 1) nodeCountAlgebra table163 = counts163 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table162 row162 counts162 193 counts162_eq (by decide +kernel)
def heights163 : Fin 163 → Nat := extend heights162 9
theorem heights163_eq : Table.fold (fun _ => 0) heightAlgebra table163 = heights163 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table162 row162 heights162 9 heights162_eq (by decide +kernel)
def row163 : Row 163 := Row.node (Kind.vector 2) (List.get ([⟨126, by decide⟩, ⟨147, by decide⟩] : List (Fin 163)))
def table164 : Table 164 := .push table163 row163
def counts164 : Fin 164 → Nat := extend counts163 193
theorem counts164_eq : Table.fold (fun _ => 1) nodeCountAlgebra table164 = counts164 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table163 row163 counts163 193 counts163_eq (by decide +kernel)
def heights164 : Fin 164 → Nat := extend heights163 9
theorem heights164_eq : Table.fold (fun _ => 0) heightAlgebra table164 = heights164 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table163 row163 heights163 9 heights163_eq (by decide +kernel)
def row164 : Row 164 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨161, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 164))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 164))) slot.1)
def table165 : Table 165 := .push table164 row164
def counts165 : Fin 165 → Nat := extend counts164 204
theorem counts165_eq : Table.fold (fun _ => 1) nodeCountAlgebra table165 = counts165 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table164 row164 counts164 204 counts164_eq (by decide +kernel)
def heights165 : Fin 165 → Nat := extend heights164 10
theorem heights165_eq : Table.fold (fun _ => 0) heightAlgebra table165 = heights165 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table164 row164 heights164 10 heights164_eq (by decide +kernel)
def row165 : Row 165 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨162, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 165))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 165))) slot.1)
def table166 : Table 166 := .push table165 row165
def counts166 : Fin 166 → Nat := extend counts165 204
theorem counts166_eq : Table.fold (fun _ => 1) nodeCountAlgebra table166 = counts166 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table165 row165 counts165 204 counts165_eq (by decide +kernel)
def heights166 : Fin 166 → Nat := extend heights165 10
theorem heights166_eq : Table.fold (fun _ => 0) heightAlgebra table166 = heights166 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table165 row165 heights165 10 heights165_eq (by decide +kernel)
def row166 : Row 166 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨156, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 166))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 166))) slot.1)
def table167 : Table 167 := .push table166 row166
def counts167 : Fin 167 → Nat := extend counts166 204
theorem counts167_eq : Table.fold (fun _ => 1) nodeCountAlgebra table167 = counts167 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table166 row166 counts166 204 counts166_eq (by decide +kernel)
def heights167 : Fin 167 → Nat := extend heights166 10
theorem heights167_eq : Table.fold (fun _ => 0) heightAlgebra table167 = heights167 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table166 row166 heights166 10 heights166_eq (by decide +kernel)
def row167 : Row 167 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨163, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 167))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 167))) slot.1)
def table168 : Table 168 := .push table167 row167
def counts168 : Fin 168 → Nat := extend counts167 204
theorem counts168_eq : Table.fold (fun _ => 1) nodeCountAlgebra table168 = counts168 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table167 row167 counts167 204 counts167_eq (by decide +kernel)
def heights168 : Fin 168 → Nat := extend heights167 10
theorem heights168_eq : Table.fold (fun _ => 0) heightAlgebra table168 = heights168 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table167 row167 heights167 10 heights167_eq (by decide +kernel)
def row168 : Row 168 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨157, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 168))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 168))) slot.1)
def table169 : Table 169 := .push table168 row168
def counts169 : Fin 169 → Nat := extend counts168 204
theorem counts169_eq : Table.fold (fun _ => 1) nodeCountAlgebra table169 = counts169 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table168 row168 counts168 204 counts168_eq (by decide +kernel)
def heights169 : Fin 169 → Nat := extend heights168 10
theorem heights169_eq : Table.fold (fun _ => 0) heightAlgebra table169 = heights169 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table168 row168 heights168 10 heights168_eq (by decide +kernel)
def row169 : Row 169 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨158, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 169))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 169))) slot.1)
def table170 : Table 170 := .push table169 row169
def counts170 : Fin 170 → Nat := extend counts169 204
theorem counts170_eq : Table.fold (fun _ => 1) nodeCountAlgebra table170 = counts170 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table169 row169 counts169 204 counts169_eq (by decide +kernel)
def heights170 : Fin 170 → Nat := extend heights169 10
theorem heights170_eq : Table.fold (fun _ => 0) heightAlgebra table170 = heights170 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table169 row169 heights169 10 heights169_eq (by decide +kernel)
def row170 : Row 170 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨160, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 170))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 170))) slot.1)
def table171 : Table 171 := .push table170 row170
def counts171 : Fin 171 → Nat := extend counts170 204
theorem counts171_eq : Table.fold (fun _ => 1) nodeCountAlgebra table171 = counts171 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table170 row170 counts170 204 counts170_eq (by decide +kernel)
def heights171 : Fin 171 → Nat := extend heights170 10
theorem heights171_eq : Table.fold (fun _ => 0) heightAlgebra table171 = heights171 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table170 row170 heights170 10 heights170_eq (by decide +kernel)
def row171 : Row 171 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨159, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 171))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 171))) slot.1)
def table172 : Table 172 := .push table171 row171
def counts172 : Fin 172 → Nat := extend counts171 204
theorem counts172_eq : Table.fold (fun _ => 1) nodeCountAlgebra table172 = counts172 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table171 row171 counts171 204 counts171_eq (by decide +kernel)
def heights172 : Fin 172 → Nat := extend heights171 10
theorem heights172_eq : Table.fold (fun _ => 0) heightAlgebra table172 = heights172 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table171 row171 heights171 10 heights171_eq (by decide +kernel)
def row172 : Row 172 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨155, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 172))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 172))) slot.1)
def table173 : Table 173 := .push table172 row172
def counts173 : Fin 173 → Nat := extend counts172 204
theorem counts173_eq : Table.fold (fun _ => 1) nodeCountAlgebra table173 = counts173 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table172 row172 counts172 204 counts172_eq (by decide +kernel)
def heights173 : Fin 173 → Nat := extend heights172 10
theorem heights173_eq : Table.fold (fun _ => 0) heightAlgebra table173 = heights173 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table172 row172 heights172 10 heights172_eq (by decide +kernel)
def row173 : Row 173 := Row.node (Kind.vector 2) (List.get ([⟨168, by decide⟩, ⟨172, by decide⟩] : List (Fin 173)))
def table174 : Table 174 := .push table173 row173
def counts174 : Fin 174 → Nat := extend counts173 409
theorem counts174_eq : Table.fold (fun _ => 1) nodeCountAlgebra table174 = counts174 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table173 row173 counts173 409 counts173_eq (by decide +kernel)
def heights174 : Fin 174 → Nat := extend heights173 11
theorem heights174_eq : Table.fold (fun _ => 0) heightAlgebra table174 = heights174 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table173 row173 heights173 11 heights173_eq (by decide +kernel)
def row174 : Row 174 := Row.node (Kind.vector 2) (List.get ([⟨167, by decide⟩, ⟨164, by decide⟩] : List (Fin 174)))
def table175 : Table 175 := .push table174 row174
def counts175 : Fin 175 → Nat := extend counts174 409
theorem counts175_eq : Table.fold (fun _ => 1) nodeCountAlgebra table175 = counts175 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table174 row174 counts174 409 counts174_eq (by decide +kernel)
def heights175 : Fin 175 → Nat := extend heights174 11
theorem heights175_eq : Table.fold (fun _ => 0) heightAlgebra table175 = heights175 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table174 row174 heights174 11 heights174_eq (by decide +kernel)
def row175 : Row 175 := Row.node (Kind.vector 2) (List.get ([⟨167, by decide⟩, ⟨172, by decide⟩] : List (Fin 175)))
def table176 : Table 176 := .push table175 row175
def counts176 : Fin 176 → Nat := extend counts175 409
theorem counts176_eq : Table.fold (fun _ => 1) nodeCountAlgebra table176 = counts176 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table175 row175 counts175 409 counts175_eq (by decide +kernel)
def heights176 : Fin 176 → Nat := extend heights175 11
theorem heights176_eq : Table.fold (fun _ => 0) heightAlgebra table176 = heights176 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table175 row175 heights175 11 heights175_eq (by decide +kernel)
def row176 : Row 176 := Row.node (Kind.vector 2) (List.get ([⟨172, by decide⟩, ⟨164, by decide⟩] : List (Fin 176)))
def table177 : Table 177 := .push table176 row176
def counts177 : Fin 177 → Nat := extend counts176 409
theorem counts177_eq : Table.fold (fun _ => 1) nodeCountAlgebra table177 = counts177 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table176 row176 counts176 409 counts176_eq (by decide +kernel)
def heights177 : Fin 177 → Nat := extend heights176 11
theorem heights177_eq : Table.fold (fun _ => 0) heightAlgebra table177 = heights177 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table176 row176 heights176 11 heights176_eq (by decide +kernel)
def row177 : Row 177 := Row.node (Kind.vector 2) (List.get ([⟨167, by decide⟩, ⟨165, by decide⟩] : List (Fin 177)))
def table178 : Table 178 := .push table177 row177
def counts178 : Fin 178 → Nat := extend counts177 409
theorem counts178_eq : Table.fold (fun _ => 1) nodeCountAlgebra table178 = counts178 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table177 row177 counts177 409 counts177_eq (by decide +kernel)
def heights178 : Fin 178 → Nat := extend heights177 11
theorem heights178_eq : Table.fold (fun _ => 0) heightAlgebra table178 = heights178 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table177 row177 heights177 11 heights177_eq (by decide +kernel)
def row178 : Row 178 := Row.node (Kind.vector 2) (List.get ([⟨172, by decide⟩, ⟨172, by decide⟩] : List (Fin 178)))
def table179 : Table 179 := .push table178 row178
def counts179 : Fin 179 → Nat := extend counts178 409
theorem counts179_eq : Table.fold (fun _ => 1) nodeCountAlgebra table179 = counts179 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table178 row178 counts178 409 counts178_eq (by decide +kernel)
def heights179 : Fin 179 → Nat := extend heights178 11
theorem heights179_eq : Table.fold (fun _ => 0) heightAlgebra table179 = heights179 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table178 row178 heights178 11 heights178_eq (by decide +kernel)
def row179 : Row 179 := Row.node (Kind.vector 2) (List.get ([⟨168, by decide⟩, ⟨164, by decide⟩] : List (Fin 179)))
def table180 : Table 180 := .push table179 row179
def counts180 : Fin 180 → Nat := extend counts179 409
theorem counts180_eq : Table.fold (fun _ => 1) nodeCountAlgebra table180 = counts180 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table179 row179 counts179 409 counts179_eq (by decide +kernel)
def heights180 : Fin 180 → Nat := extend heights179 11
theorem heights180_eq : Table.fold (fun _ => 0) heightAlgebra table180 = heights180 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table179 row179 heights179 11 heights179_eq (by decide +kernel)
def row180 : Row 180 := Row.node (Kind.vector 2) (List.get ([⟨172, by decide⟩, ⟨165, by decide⟩] : List (Fin 180)))
def table181 : Table 181 := .push table180 row180
def counts181 : Fin 181 → Nat := extend counts180 409
theorem counts181_eq : Table.fold (fun _ => 1) nodeCountAlgebra table181 = counts181 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table180 row180 counts180 409 counts180_eq (by decide +kernel)
def heights181 : Fin 181 → Nat := extend heights180 11
theorem heights181_eq : Table.fold (fun _ => 0) heightAlgebra table181 = heights181 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table180 row180 heights180 11 heights180_eq (by decide +kernel)
def row181 : Row 181 := Row.node (Kind.vector 2) (List.get ([⟨168, by decide⟩, ⟨165, by decide⟩] : List (Fin 181)))
def table182 : Table 182 := .push table181 row181
def counts182 : Fin 182 → Nat := extend counts181 409
theorem counts182_eq : Table.fold (fun _ => 1) nodeCountAlgebra table182 = counts182 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table181 row181 counts181 409 counts181_eq (by decide +kernel)
def heights182 : Fin 182 → Nat := extend heights181 11
theorem heights182_eq : Table.fold (fun _ => 0) heightAlgebra table182 = heights182 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table181 row181 heights181 11 heights181_eq (by decide +kernel)
def row182 : Row 182 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨179, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 182))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 182))) slot.1)
def table183 : Table 183 := .push table182 row182
def counts183 : Fin 183 → Nat := extend counts182 420
theorem counts183_eq : Table.fold (fun _ => 1) nodeCountAlgebra table183 = counts183 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table182 row182 counts182 420 counts182_eq (by decide +kernel)
def heights183 : Fin 183 → Nat := extend heights182 12
theorem heights183_eq : Table.fold (fun _ => 0) heightAlgebra table183 = heights183 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table182 row182 heights182 12 heights182_eq (by decide +kernel)
def row183 : Row 183 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨178, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 183))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 183))) slot.1)
def table184 : Table 184 := .push table183 row183
def counts184 : Fin 184 → Nat := extend counts183 420
theorem counts184_eq : Table.fold (fun _ => 1) nodeCountAlgebra table184 = counts184 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table183 row183 counts183 420 counts183_eq (by decide +kernel)
def heights184 : Fin 184 → Nat := extend heights183 12
theorem heights184_eq : Table.fold (fun _ => 0) heightAlgebra table184 = heights184 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table183 row183 heights183 12 heights183_eq (by decide +kernel)
def row184 : Row 184 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨181, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 184))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 184))) slot.1)
def table185 : Table 185 := .push table184 row184
def counts185 : Fin 185 → Nat := extend counts184 420
theorem counts185_eq : Table.fold (fun _ => 1) nodeCountAlgebra table185 = counts185 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table184 row184 counts184 420 counts184_eq (by decide +kernel)
def heights185 : Fin 185 → Nat := extend heights184 12
theorem heights185_eq : Table.fold (fun _ => 0) heightAlgebra table185 = heights185 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table184 row184 heights184 12 heights184_eq (by decide +kernel)
def row185 : Row 185 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨173, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 185))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 185))) slot.1)
def table186 : Table 186 := .push table185 row185
def counts186 : Fin 186 → Nat := extend counts185 420
theorem counts186_eq : Table.fold (fun _ => 1) nodeCountAlgebra table186 = counts186 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table185 row185 counts185 420 counts185_eq (by decide +kernel)
def heights186 : Fin 186 → Nat := extend heights185 12
theorem heights186_eq : Table.fold (fun _ => 0) heightAlgebra table186 = heights186 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table185 row185 heights185 12 heights185_eq (by decide +kernel)
def row186 : Row 186 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨180, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 186))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 186))) slot.1)
def table187 : Table 187 := .push table186 row186
def counts187 : Fin 187 → Nat := extend counts186 420
theorem counts187_eq : Table.fold (fun _ => 1) nodeCountAlgebra table187 = counts187 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table186 row186 counts186 420 counts186_eq (by decide +kernel)
def heights187 : Fin 187 → Nat := extend heights186 12
theorem heights187_eq : Table.fold (fun _ => 0) heightAlgebra table187 = heights187 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table186 row186 heights186 12 heights186_eq (by decide +kernel)
def row187 : Row 187 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨175, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 187))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 187))) slot.1)
def table188 : Table 188 := .push table187 row187
def counts188 : Fin 188 → Nat := extend counts187 420
theorem counts188_eq : Table.fold (fun _ => 1) nodeCountAlgebra table188 = counts188 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table187 row187 counts187 420 counts187_eq (by decide +kernel)
def heights188 : Fin 188 → Nat := extend heights187 12
theorem heights188_eq : Table.fold (fun _ => 0) heightAlgebra table188 = heights188 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table187 row187 heights187 12 heights187_eq (by decide +kernel)
def row188 : Row 188 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨177, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 188))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 188))) slot.1)
def table189 : Table 189 := .push table188 row188
def counts189 : Fin 189 → Nat := extend counts188 420
theorem counts189_eq : Table.fold (fun _ => 1) nodeCountAlgebra table189 = counts189 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table188 row188 counts188 420 counts188_eq (by decide +kernel)
def heights189 : Fin 189 → Nat := extend heights188 12
theorem heights189_eq : Table.fold (fun _ => 0) heightAlgebra table189 = heights189 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table188 row188 heights188 12 heights188_eq (by decide +kernel)
def row189 : Row 189 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨174, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 189))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 189))) slot.1)
def table190 : Table 190 := .push table189 row189
def counts190 : Fin 190 → Nat := extend counts189 420
theorem counts190_eq : Table.fold (fun _ => 1) nodeCountAlgebra table190 = counts190 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table189 row189 counts189 420 counts189_eq (by decide +kernel)
def heights190 : Fin 190 → Nat := extend heights189 12
theorem heights190_eq : Table.fold (fun _ => 0) heightAlgebra table190 = heights190 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table189 row189 heights189 12 heights189_eq (by decide +kernel)
def row190 : Row 190 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨176, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 190))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 190))) slot.1)
def table191 : Table 191 := .push table190 row190
def counts191 : Fin 191 → Nat := extend counts190 420
theorem counts191_eq : Table.fold (fun _ => 1) nodeCountAlgebra table191 = counts191 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table190 row190 counts190 420 counts190_eq (by decide +kernel)
def heights191 : Fin 191 → Nat := extend heights190 12
theorem heights191_eq : Table.fold (fun _ => 0) heightAlgebra table191 = heights191 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table190 row190 heights190 12 heights190_eq (by decide +kernel)
def row191 : Row 191 := Row.node (Kind.vector 2) (List.get ([⟨169, by decide⟩, ⟨188, by decide⟩] : List (Fin 191)))
def table192 : Table 192 := .push table191 row191
def counts192 : Fin 192 → Nat := extend counts191 625
theorem counts192_eq : Table.fold (fun _ => 1) nodeCountAlgebra table192 = counts192 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table191 row191 counts191 625 counts191_eq (by decide +kernel)
def heights192 : Fin 192 → Nat := extend heights191 13
theorem heights192_eq : Table.fold (fun _ => 0) heightAlgebra table192 = heights192 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table191 row191 heights191 13 heights191_eq (by decide +kernel)
def row192 : Row 192 := Row.node (Kind.vector 2) (List.get ([⟨165, by decide⟩, ⟨186, by decide⟩] : List (Fin 192)))
def table193 : Table 193 := .push table192 row192
def counts193 : Fin 193 → Nat := extend counts192 625
theorem counts193_eq : Table.fold (fun _ => 1) nodeCountAlgebra table193 = counts193 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table192 row192 counts192 625 counts192_eq (by decide +kernel)
def heights193 : Fin 193 → Nat := extend heights192 13
theorem heights193_eq : Table.fold (fun _ => 0) heightAlgebra table193 = heights193 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table192 row192 heights192 13 heights192_eq (by decide +kernel)
def row193 : Row 193 := Row.node (Kind.vector 2) (List.get ([⟨172, by decide⟩, ⟨183, by decide⟩] : List (Fin 193)))
def table194 : Table 194 := .push table193 row193
def counts194 : Fin 194 → Nat := extend counts193 625
theorem counts194_eq : Table.fold (fun _ => 1) nodeCountAlgebra table194 = counts194 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table193 row193 counts193 625 counts193_eq (by decide +kernel)
def heights194 : Fin 194 → Nat := extend heights193 13
theorem heights194_eq : Table.fold (fun _ => 0) heightAlgebra table194 = heights194 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table193 row193 heights193 13 heights193_eq (by decide +kernel)
def row194 : Row 194 := Row.node (Kind.vector 2) (List.get ([⟨167, by decide⟩, ⟨187, by decide⟩] : List (Fin 194)))
def table195 : Table 195 := .push table194 row194
def counts195 : Fin 195 → Nat := extend counts194 625
theorem counts195_eq : Table.fold (fun _ => 1) nodeCountAlgebra table195 = counts195 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table194 row194 counts194 625 counts194_eq (by decide +kernel)
def heights195 : Fin 195 → Nat := extend heights194 13
theorem heights195_eq : Table.fold (fun _ => 0) heightAlgebra table195 = heights195 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table194 row194 heights194 13 heights194_eq (by decide +kernel)
def row195 : Row 195 := Row.node (Kind.vector 2) (List.get ([⟨164, by decide⟩, ⟨190, by decide⟩] : List (Fin 195)))
def table196 : Table 196 := .push table195 row195
def counts196 : Fin 196 → Nat := extend counts195 625
theorem counts196_eq : Table.fold (fun _ => 1) nodeCountAlgebra table196 = counts196 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table195 row195 counts195 625 counts195_eq (by decide +kernel)
def heights196 : Fin 196 → Nat := extend heights195 13
theorem heights196_eq : Table.fold (fun _ => 0) heightAlgebra table196 = heights196 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table195 row195 heights195 13 heights195_eq (by decide +kernel)
def row196 : Row 196 := Row.node (Kind.vector 2) (List.get ([⟨170, by decide⟩, ⟨182, by decide⟩] : List (Fin 196)))
def table197 : Table 197 := .push table196 row196
def counts197 : Fin 197 → Nat := extend counts196 625
theorem counts197_eq : Table.fold (fun _ => 1) nodeCountAlgebra table197 = counts197 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table196 row196 counts196 625 counts196_eq (by decide +kernel)
def heights197 : Fin 197 → Nat := extend heights196 13
theorem heights197_eq : Table.fold (fun _ => 0) heightAlgebra table197 = heights197 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table196 row196 heights196 13 heights196_eq (by decide +kernel)
def row197 : Row 197 := Row.node (Kind.vector 2) (List.get ([⟨166, by decide⟩, ⟨189, by decide⟩] : List (Fin 197)))
def table198 : Table 198 := .push table197 row197
def counts198 : Fin 198 → Nat := extend counts197 625
theorem counts198_eq : Table.fold (fun _ => 1) nodeCountAlgebra table198 = counts198 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table197 row197 counts197 625 counts197_eq (by decide +kernel)
def heights198 : Fin 198 → Nat := extend heights197 13
theorem heights198_eq : Table.fold (fun _ => 0) heightAlgebra table198 = heights198 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table197 row197 heights197 13 heights197_eq (by decide +kernel)
def row198 : Row 198 := Row.node (Kind.vector 2) (List.get ([⟨171, by decide⟩, ⟨184, by decide⟩] : List (Fin 198)))
def table199 : Table 199 := .push table198 row198
def counts199 : Fin 199 → Nat := extend counts198 625
theorem counts199_eq : Table.fold (fun _ => 1) nodeCountAlgebra table199 = counts199 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table198 row198 counts198 625 counts198_eq (by decide +kernel)
def heights199 : Fin 199 → Nat := extend heights198 13
theorem heights199_eq : Table.fold (fun _ => 0) heightAlgebra table199 = heights199 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table198 row198 heights198 13 heights198_eq (by decide +kernel)
def row199 : Row 199 := Row.node (Kind.vector 2) (List.get ([⟨168, by decide⟩, ⟨185, by decide⟩] : List (Fin 199)))
def table200 : Table 200 := .push table199 row199
def counts200 : Fin 200 → Nat := extend counts199 625
theorem counts200_eq : Table.fold (fun _ => 1) nodeCountAlgebra table200 = counts200 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table199 row199 counts199 625 counts199_eq (by decide +kernel)
def heights200 : Fin 200 → Nat := extend heights199 13
theorem heights200_eq : Table.fold (fun _ => 0) heightAlgebra table200 = heights200 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table199 row199 heights199 13 heights199_eq (by decide +kernel)
def row200 : Row 200 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨199, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 200))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 200))) slot.1)
def table201 : Table 201 := .push table200 row200
def counts201 : Fin 201 → Nat := extend counts200 636
theorem counts201_eq : Table.fold (fun _ => 1) nodeCountAlgebra table201 = counts201 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table200 row200 counts200 636 counts200_eq (by decide +kernel)
def heights201 : Fin 201 → Nat := extend heights200 14
theorem heights201_eq : Table.fold (fun _ => 0) heightAlgebra table201 = heights201 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table200 row200 heights200 14 heights200_eq (by decide +kernel)
def row201 : Row 201 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨197, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 201))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 201))) slot.1)
def table202 : Table 202 := .push table201 row201
def counts202 : Fin 202 → Nat := extend counts201 636
theorem counts202_eq : Table.fold (fun _ => 1) nodeCountAlgebra table202 = counts202 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table201 row201 counts201 636 counts201_eq (by decide +kernel)
def heights202 : Fin 202 → Nat := extend heights201 14
theorem heights202_eq : Table.fold (fun _ => 0) heightAlgebra table202 = heights202 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table201 row201 heights201 14 heights201_eq (by decide +kernel)
def row202 : Row 202 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨195, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 202))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 202))) slot.1)
def table203 : Table 203 := .push table202 row202
def counts203 : Fin 203 → Nat := extend counts202 636
theorem counts203_eq : Table.fold (fun _ => 1) nodeCountAlgebra table203 = counts203 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table202 row202 counts202 636 counts202_eq (by decide +kernel)
def heights203 : Fin 203 → Nat := extend heights202 14
theorem heights203_eq : Table.fold (fun _ => 0) heightAlgebra table203 = heights203 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table202 row202 heights202 14 heights202_eq (by decide +kernel)
def row203 : Row 203 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨191, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 203))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 203))) slot.1)
def table204 : Table 204 := .push table203 row203
def counts204 : Fin 204 → Nat := extend counts203 636
theorem counts204_eq : Table.fold (fun _ => 1) nodeCountAlgebra table204 = counts204 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table203 row203 counts203 636 counts203_eq (by decide +kernel)
def heights204 : Fin 204 → Nat := extend heights203 14
theorem heights204_eq : Table.fold (fun _ => 0) heightAlgebra table204 = heights204 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table203 row203 heights203 14 heights203_eq (by decide +kernel)
def row204 : Row 204 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨196, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 204))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 204))) slot.1)
def table205 : Table 205 := .push table204 row204
def counts205 : Fin 205 → Nat := extend counts204 636
theorem counts205_eq : Table.fold (fun _ => 1) nodeCountAlgebra table205 = counts205 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table204 row204 counts204 636 counts204_eq (by decide +kernel)
def heights205 : Fin 205 → Nat := extend heights204 14
theorem heights205_eq : Table.fold (fun _ => 0) heightAlgebra table205 = heights205 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table204 row204 heights204 14 heights204_eq (by decide +kernel)
def row205 : Row 205 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨194, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 205))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 205))) slot.1)
def table206 : Table 206 := .push table205 row205
def counts206 : Fin 206 → Nat := extend counts205 636
theorem counts206_eq : Table.fold (fun _ => 1) nodeCountAlgebra table206 = counts206 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table205 row205 counts205 636 counts205_eq (by decide +kernel)
def heights206 : Fin 206 → Nat := extend heights205 14
theorem heights206_eq : Table.fold (fun _ => 0) heightAlgebra table206 = heights206 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table205 row205 heights205 14 heights205_eq (by decide +kernel)
def row206 : Row 206 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨193, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 206))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 206))) slot.1)
def table207 : Table 207 := .push table206 row206
def counts207 : Fin 207 → Nat := extend counts206 636
theorem counts207_eq : Table.fold (fun _ => 1) nodeCountAlgebra table207 = counts207 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table206 row206 counts206 636 counts206_eq (by decide +kernel)
def heights207 : Fin 207 → Nat := extend heights206 14
theorem heights207_eq : Table.fold (fun _ => 0) heightAlgebra table207 = heights207 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table206 row206 heights206 14 heights206_eq (by decide +kernel)
def row207 : Row 207 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨192, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 207))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 207))) slot.1)
def table208 : Table 208 := .push table207 row207
def counts208 : Fin 208 → Nat := extend counts207 636
theorem counts208_eq : Table.fold (fun _ => 1) nodeCountAlgebra table208 = counts208 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table207 row207 counts207 636 counts207_eq (by decide +kernel)
def heights208 : Fin 208 → Nat := extend heights207 14
theorem heights208_eq : Table.fold (fun _ => 0) heightAlgebra table208 = heights208 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table207 row207 heights207 14 heights207_eq (by decide +kernel)
def row208 : Row 208 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨198, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨27, by decide⟩] : List (Fin 208))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 208))) slot.1)
def table209 : Table 209 := .push table208 row208
def counts209 : Fin 209 → Nat := extend counts208 636
theorem counts209_eq : Table.fold (fun _ => 1) nodeCountAlgebra table209 = counts209 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table208 row208 counts208 636 counts208_eq (by decide +kernel)
def heights209 : Fin 209 → Nat := extend heights208 14
theorem heights209_eq : Table.fold (fun _ => 0) heightAlgebra table209 = heights209 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table208 row208 heights208 14 heights208_eq (by decide +kernel)
def row209 : Row 209 := Row.node (Kind.vector 2) (List.get ([⟨205, by decide⟩, ⟨207, by decide⟩] : List (Fin 209)))
def table210 : Table 210 := .push table209 row209
def counts210 : Fin 210 → Nat := extend counts209 1273
theorem counts210_eq : Table.fold (fun _ => 1) nodeCountAlgebra table210 = counts210 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table209 row209 counts209 1273 counts209_eq (by decide +kernel)
def heights210 : Fin 210 → Nat := extend heights209 15
theorem heights210_eq : Table.fold (fun _ => 0) heightAlgebra table210 = heights210 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table209 row209 heights209 15 heights209_eq (by decide +kernel)
def row210 : Row 210 := Row.node (Kind.vector 3) (List.get ([⟨203, by decide⟩, ⟨201, by decide⟩, ⟨205, by decide⟩] : List (Fin 210)))
def table211 : Table 211 := .push table210 row210
def counts211 : Fin 211 → Nat := extend counts210 1909
theorem counts211_eq : Table.fold (fun _ => 1) nodeCountAlgebra table211 = counts211 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table210 row210 counts210 1909 counts210_eq (by decide +kernel)
def heights211 : Fin 211 → Nat := extend heights210 15
theorem heights211_eq : Table.fold (fun _ => 0) heightAlgebra table211 = heights211 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table210 row210 heights210 15 heights210_eq (by decide +kernel)
def row211 : Row 211 := Row.node (Kind.vector 2) (List.get ([⟨208, by decide⟩, ⟨208, by decide⟩] : List (Fin 211)))
def table212 : Table 212 := .push table211 row211
def counts212 : Fin 212 → Nat := extend counts211 1273
theorem counts212_eq : Table.fold (fun _ => 1) nodeCountAlgebra table212 = counts212 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table211 row211 counts211 1273 counts211_eq (by decide +kernel)
def heights212 : Fin 212 → Nat := extend heights211 15
theorem heights212_eq : Table.fold (fun _ => 0) heightAlgebra table212 = heights212 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table211 row211 heights211 15 heights211_eq (by decide +kernel)
def row212 : Row 212 := Row.node (Kind.vector 2) (List.get ([⟨208, by decide⟩, ⟨204, by decide⟩] : List (Fin 212)))
def table213 : Table 213 := .push table212 row212
def counts213 : Fin 213 → Nat := extend counts212 1273
theorem counts213_eq : Table.fold (fun _ => 1) nodeCountAlgebra table213 = counts213 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table212 row212 counts212 1273 counts212_eq (by decide +kernel)
def heights213 : Fin 213 → Nat := extend heights212 15
theorem heights213_eq : Table.fold (fun _ => 0) heightAlgebra table213 = heights213 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table212 row212 heights212 15 heights212_eq (by decide +kernel)
def row213 : Row 213 := Row.node (Kind.vector 2) (List.get ([⟨207, by decide⟩, ⟨208, by decide⟩] : List (Fin 213)))
def table214 : Table 214 := .push table213 row213
def counts214 : Fin 214 → Nat := extend counts213 1273
theorem counts214_eq : Table.fold (fun _ => 1) nodeCountAlgebra table214 = counts214 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table213 row213 counts213 1273 counts213_eq (by decide +kernel)
def heights214 : Fin 214 → Nat := extend heights213 15
theorem heights214_eq : Table.fold (fun _ => 0) heightAlgebra table214 = heights214 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table213 row213 heights213 15 heights213_eq (by decide +kernel)
def row214 : Row 214 := Row.node (Kind.vector 2) (List.get ([⟨201, by decide⟩, ⟨201, by decide⟩] : List (Fin 214)))
def table215 : Table 215 := .push table214 row214
def counts215 : Fin 215 → Nat := extend counts214 1273
theorem counts215_eq : Table.fold (fun _ => 1) nodeCountAlgebra table215 = counts215 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table214 row214 counts214 1273 counts214_eq (by decide +kernel)
def heights215 : Fin 215 → Nat := extend heights214 15
theorem heights215_eq : Table.fold (fun _ => 0) heightAlgebra table215 = heights215 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table214 row214 heights214 15 heights214_eq (by decide +kernel)
def row215 : Row 215 := Row.node (Kind.vector 2) (List.get ([⟨202, by decide⟩, ⟨201, by decide⟩] : List (Fin 215)))
def table216 : Table 216 := .push table215 row215
def counts216 : Fin 216 → Nat := extend counts215 1273
theorem counts216_eq : Table.fold (fun _ => 1) nodeCountAlgebra table216 = counts216 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table215 row215 counts215 1273 counts215_eq (by decide +kernel)
def heights216 : Fin 216 → Nat := extend heights215 15
theorem heights216_eq : Table.fold (fun _ => 0) heightAlgebra table216 = heights216 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table215 row215 heights215 15 heights215_eq (by decide +kernel)
def row216 : Row 216 := Row.node (Kind.vector 2) (List.get ([⟨202, by decide⟩, ⟨203, by decide⟩] : List (Fin 216)))
def table217 : Table 217 := .push table216 row216
def counts217 : Fin 217 → Nat := extend counts216 1273
theorem counts217_eq : Table.fold (fun _ => 1) nodeCountAlgebra table217 = counts217 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table216 row216 counts216 1273 counts216_eq (by decide +kernel)
def heights217 : Fin 217 → Nat := extend heights216 15
theorem heights217_eq : Table.fold (fun _ => 0) heightAlgebra table217 = heights217 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table216 row216 heights216 15 heights216_eq (by decide +kernel)
def row217 : Row 217 := Row.node (Kind.vector 3) (List.get ([⟨207, by decide⟩, ⟨202, by decide⟩, ⟨206, by decide⟩] : List (Fin 217)))
def table218 : Table 218 := .push table217 row217
def counts218 : Fin 218 → Nat := extend counts217 1909
theorem counts218_eq : Table.fold (fun _ => 1) nodeCountAlgebra table218 = counts218 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table217 row217 counts217 1909 counts217_eq (by decide +kernel)
def heights218 : Fin 218 → Nat := extend heights217 15
theorem heights218_eq : Table.fold (fun _ => 0) heightAlgebra table218 = heights218 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table217 row217 heights217 15 heights217_eq (by decide +kernel)
def row218 : Row 218 := Row.node (Kind.vector 2) (List.get ([⟨202, by decide⟩, ⟨205, by decide⟩] : List (Fin 218)))
def table219 : Table 219 := .push table218 row218
def counts219 : Fin 219 → Nat := extend counts218 1273
theorem counts219_eq : Table.fold (fun _ => 1) nodeCountAlgebra table219 = counts219 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table218 row218 counts218 1273 counts218_eq (by decide +kernel)
def heights219 : Fin 219 → Nat := extend heights218 15
theorem heights219_eq : Table.fold (fun _ => 0) heightAlgebra table219 = heights219 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table218 row218 heights218 15 heights218_eq (by decide +kernel)
def row219 : Row 219 := Row.node (Kind.vector 2) (List.get ([⟨205, by decide⟩, ⟨206, by decide⟩] : List (Fin 219)))
def table220 : Table 220 := .push table219 row219
def counts220 : Fin 220 → Nat := extend counts219 1273
theorem counts220_eq : Table.fold (fun _ => 1) nodeCountAlgebra table220 = counts220 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table219 row219 counts219 1273 counts219_eq (by decide +kernel)
def heights220 : Fin 220 → Nat := extend heights219 15
theorem heights220_eq : Table.fold (fun _ => 0) heightAlgebra table220 = heights220 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table219 row219 heights219 15 heights219_eq (by decide +kernel)
def row220 : Row 220 := Row.node (Kind.vector 2) (List.get ([⟨204, by decide⟩, ⟨205, by decide⟩] : List (Fin 220)))
def table221 : Table 221 := .push table220 row220
def counts221 : Fin 221 → Nat := extend counts220 1273
theorem counts221_eq : Table.fold (fun _ => 1) nodeCountAlgebra table221 = counts221 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table220 row220 counts220 1273 counts220_eq (by decide +kernel)
def heights221 : Fin 221 → Nat := extend heights220 15
theorem heights221_eq : Table.fold (fun _ => 0) heightAlgebra table221 = heights221 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table220 row220 heights220 15 heights220_eq (by decide +kernel)
def row221 : Row 221 := Row.node (Kind.vector 2) (List.get ([⟨208, by decide⟩, ⟨200, by decide⟩] : List (Fin 221)))
def table222 : Table 222 := .push table221 row221
def counts222 : Fin 222 → Nat := extend counts221 1273
theorem counts222_eq : Table.fold (fun _ => 1) nodeCountAlgebra table222 = counts222 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table221 row221 counts221 1273 counts221_eq (by decide +kernel)
def heights222 : Fin 222 → Nat := extend heights221 15
theorem heights222_eq : Table.fold (fun _ => 0) heightAlgebra table222 = heights222 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table221 row221 heights221 15 heights221_eq (by decide +kernel)
def row222 : Row 222 := Row.node (Kind.vector 2) (List.get ([⟨204, by decide⟩, ⟨203, by decide⟩] : List (Fin 222)))
def table223 : Table 223 := .push table222 row222
def counts223 : Fin 223 → Nat := extend counts222 1273
theorem counts223_eq : Table.fold (fun _ => 1) nodeCountAlgebra table223 = counts223 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table222 row222 counts222 1273 counts222_eq (by decide +kernel)
def heights223 : Fin 223 → Nat := extend heights222 15
theorem heights223_eq : Table.fold (fun _ => 0) heightAlgebra table223 = heights223 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table222 row222 heights222 15 heights222_eq (by decide +kernel)
def row223 : Row 223 := Row.node (Kind.vector 3) (List.get ([⟨208, by decide⟩, ⟨204, by decide⟩, ⟨200, by decide⟩] : List (Fin 223)))
def table224 : Table 224 := .push table223 row223
def counts224 : Fin 224 → Nat := extend counts223 1909
theorem counts224_eq : Table.fold (fun _ => 1) nodeCountAlgebra table224 = counts224 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table223 row223 counts223 1909 counts223_eq (by decide +kernel)
def heights224 : Fin 224 → Nat := extend heights223 15
theorem heights224_eq : Table.fold (fun _ => 0) heightAlgebra table224 = heights224 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table223 row223 heights223 15 heights223_eq (by decide +kernel)
def row224 : Row 224 := Row.node (Kind.vector 2) (List.get ([⟨203, by decide⟩, ⟨200, by decide⟩] : List (Fin 224)))
def table225 : Table 225 := .push table224 row224
def counts225 : Fin 225 → Nat := extend counts224 1273
theorem counts225_eq : Table.fold (fun _ => 1) nodeCountAlgebra table225 = counts225 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table224 row224 counts224 1273 counts224_eq (by decide +kernel)
def heights225 : Fin 225 → Nat := extend heights224 15
theorem heights225_eq : Table.fold (fun _ => 0) heightAlgebra table225 = heights225 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table224 row224 heights224 15 heights224_eq (by decide +kernel)
def row225 : Row 225 := Row.node (Kind.vector 2) (List.get ([⟨200, by decide⟩, ⟨202, by decide⟩] : List (Fin 225)))
def table226 : Table 226 := .push table225 row225
def counts226 : Fin 226 → Nat := extend counts225 1273
theorem counts226_eq : Table.fold (fun _ => 1) nodeCountAlgebra table226 = counts226 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table225 row225 counts225 1273 counts225_eq (by decide +kernel)
def heights226 : Fin 226 → Nat := extend heights225 15
theorem heights226_eq : Table.fold (fun _ => 0) heightAlgebra table226 = heights226 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table225 row225 heights225 15 heights225_eq (by decide +kernel)
def row226 : Row 226 := Row.node (Kind.vector 2) (List.get ([⟨204, by decide⟩, ⟨201, by decide⟩] : List (Fin 226)))
def table227 : Table 227 := .push table226 row226
def counts227 : Fin 227 → Nat := extend counts226 1273
theorem counts227_eq : Table.fold (fun _ => 1) nodeCountAlgebra table227 = counts227 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table226 row226 counts226 1273 counts226_eq (by decide +kernel)
def heights227 : Fin 227 → Nat := extend heights226 15
theorem heights227_eq : Table.fold (fun _ => 0) heightAlgebra table227 = heights227 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table226 row226 heights226 15 heights226_eq (by decide +kernel)
def row227 : Row 227 := Row.node (Kind.vector 2) (List.get ([⟨203, by decide⟩, ⟨204, by decide⟩] : List (Fin 227)))
def table228 : Table 228 := .push table227 row227
def counts228 : Fin 228 → Nat := extend counts227 1273
theorem counts228_eq : Table.fold (fun _ => 1) nodeCountAlgebra table228 = counts228 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table227 row227 counts227 1273 counts227_eq (by decide +kernel)
def heights228 : Fin 228 → Nat := extend heights227 15
theorem heights228_eq : Table.fold (fun _ => 0) heightAlgebra table228 = heights228 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table227 row227 heights227 15 heights227_eq (by decide +kernel)
def row228 : Row 228 := Row.node (Kind.vector 2) (List.get ([⟨201, by decide⟩, ⟨205, by decide⟩] : List (Fin 228)))
def table229 : Table 229 := .push table228 row228
def counts229 : Fin 229 → Nat := extend counts228 1273
theorem counts229_eq : Table.fold (fun _ => 1) nodeCountAlgebra table229 = counts229 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table228 row228 counts228 1273 counts228_eq (by decide +kernel)
def heights229 : Fin 229 → Nat := extend heights228 15
theorem heights229_eq : Table.fold (fun _ => 0) heightAlgebra table229 = heights229 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table228 row228 heights228 15 heights228_eq (by decide +kernel)
def row229 : Row 229 := Row.node (Kind.vector 2) (List.get ([⟨206, by decide⟩, ⟨206, by decide⟩] : List (Fin 229)))
def table230 : Table 230 := .push table229 row229
def counts230 : Fin 230 → Nat := extend counts229 1273
theorem counts230_eq : Table.fold (fun _ => 1) nodeCountAlgebra table230 = counts230 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table229 row229 counts229 1273 counts229_eq (by decide +kernel)
def heights230 : Fin 230 → Nat := extend heights229 15
theorem heights230_eq : Table.fold (fun _ => 0) heightAlgebra table230 = heights230 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table229 row229 heights229 15 heights229_eq (by decide +kernel)
def row230 : Row 230 := Row.node (Kind.vector 2) (List.get ([⟨206, by decide⟩, ⟨207, by decide⟩] : List (Fin 230)))
def table231 : Table 231 := .push table230 row230
def counts231 : Fin 231 → Nat := extend counts230 1273
theorem counts231_eq : Table.fold (fun _ => 1) nodeCountAlgebra table231 = counts231 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table230 row230 counts230 1273 counts230_eq (by decide +kernel)
def heights231 : Fin 231 → Nat := extend heights230 15
theorem heights231_eq : Table.fold (fun _ => 0) heightAlgebra table231 = heights231 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table230 row230 heights230 15 heights230_eq (by decide +kernel)
def row231 : Row 231 := Row.node (Kind.vector 2) (List.get ([⟨200, by decide⟩, ⟨206, by decide⟩] : List (Fin 231)))
def table232 : Table 232 := .push table231 row231
def counts232 : Fin 232 → Nat := extend counts231 1273
theorem counts232_eq : Table.fold (fun _ => 1) nodeCountAlgebra table232 = counts232 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table231 row231 counts231 1273 counts231_eq (by decide +kernel)
def heights232 : Fin 232 → Nat := extend heights231 15
theorem heights232_eq : Table.fold (fun _ => 0) heightAlgebra table232 = heights232 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table231 row231 heights231 15 heights231_eq (by decide +kernel)
def row232 : Row 232 := Row.node (Kind.vector 2) (List.get ([⟨203, by decide⟩, ⟨208, by decide⟩] : List (Fin 232)))
def table233 : Table 233 := .push table232 row232
def counts233 : Fin 233 → Nat := extend counts232 1273
theorem counts233_eq : Table.fold (fun _ => 1) nodeCountAlgebra table233 = counts233 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table232 row232 counts232 1273 counts232_eq (by decide +kernel)
def heights233 : Fin 233 → Nat := extend heights232 15
theorem heights233_eq : Table.fold (fun _ => 0) heightAlgebra table233 = heights233 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table232 row232 heights232 15 heights232_eq (by decide +kernel)
def row233 : Row 233 := Row.node (Kind.vector 2) (List.get ([⟨206, by decide⟩, ⟨202, by decide⟩] : List (Fin 233)))
def table234 : Table 234 := .push table233 row233
def counts234 : Fin 234 → Nat := extend counts233 1273
theorem counts234_eq : Table.fold (fun _ => 1) nodeCountAlgebra table234 = counts234 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table233 row233 counts233 1273 counts233_eq (by decide +kernel)
def heights234 : Fin 234 → Nat := extend heights233 15
theorem heights234_eq : Table.fold (fun _ => 0) heightAlgebra table234 = heights234 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table233 row233 heights233 15 heights233_eq (by decide +kernel)
def row234 : Row 234 := Row.node (Kind.vector 2) (List.get ([⟨205, by decide⟩, ⟨202, by decide⟩] : List (Fin 234)))
def table235 : Table 235 := .push table234 row234
def counts235 : Fin 235 → Nat := extend counts234 1273
theorem counts235_eq : Table.fold (fun _ => 1) nodeCountAlgebra table235 = counts235 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table234 row234 counts234 1273 counts234_eq (by decide +kernel)
def heights235 : Fin 235 → Nat := extend heights234 15
theorem heights235_eq : Table.fold (fun _ => 0) heightAlgebra table235 = heights235 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table234 row234 heights234 15 heights234_eq (by decide +kernel)
def row235 : Row 235 := Row.node (Kind.vector 2) (List.get ([⟨207, by decide⟩, ⟨200, by decide⟩] : List (Fin 235)))
def table236 : Table 236 := .push table235 row235
def counts236 : Fin 236 → Nat := extend counts235 1273
theorem counts236_eq : Table.fold (fun _ => 1) nodeCountAlgebra table236 = counts236 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table235 row235 counts235 1273 counts235_eq (by decide +kernel)
def heights236 : Fin 236 → Nat := extend heights235 15
theorem heights236_eq : Table.fold (fun _ => 0) heightAlgebra table236 = heights236 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table235 row235 heights235 15 heights235_eq (by decide +kernel)
def row236 : Row 236 := Row.node (Kind.vector 2) (List.get ([⟨207, by decide⟩, ⟨204, by decide⟩] : List (Fin 236)))
def table237 : Table 237 := .push table236 row236
def counts237 : Fin 237 → Nat := extend counts236 1273
theorem counts237_eq : Table.fold (fun _ => 1) nodeCountAlgebra table237 = counts237 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table236 row236 counts236 1273 counts236_eq (by decide +kernel)
def heights237 : Fin 237 → Nat := extend heights236 15
theorem heights237_eq : Table.fold (fun _ => 0) heightAlgebra table237 = heights237 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table236 row236 heights236 15 heights236_eq (by decide +kernel)
def row237 : Row 237 := Row.node (Kind.vector 2) (List.get ([⟨201, by decide⟩, ⟨203, by decide⟩] : List (Fin 237)))
def table238 : Table 238 := .push table237 row237
def counts238 : Fin 238 → Nat := extend counts237 1273
theorem counts238_eq : Table.fold (fun _ => 1) nodeCountAlgebra table238 = counts238 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table237 row237 counts237 1273 counts237_eq (by decide +kernel)
def heights238 : Fin 238 → Nat := extend heights237 15
theorem heights238_eq : Table.fold (fun _ => 0) heightAlgebra table238 = heights238 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table237 row237 heights237 15 heights237_eq (by decide +kernel)
def row238 : Row 238 := Row.node (Kind.vector 2) (List.get ([⟨200, by decide⟩, ⟨207, by decide⟩] : List (Fin 238)))
def table239 : Table 239 := .push table238 row238
def counts239 : Fin 239 → Nat := extend counts238 1273
theorem counts239_eq : Table.fold (fun _ => 1) nodeCountAlgebra table239 = counts239 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table238 row238 counts238 1273 counts238_eq (by decide +kernel)
def heights239 : Fin 239 → Nat := extend heights238 15
theorem heights239_eq : Table.fold (fun _ => 0) heightAlgebra table239 = heights239 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table238 row238 heights238 15 heights238_eq (by decide +kernel)
def row239 : Row 239 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨215, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 239))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 239))) slot.1)
def table240 : Table 240 := .push table239 row239
def counts240 : Fin 240 → Nat := extend counts239 1284
theorem counts240_eq : Table.fold (fun _ => 1) nodeCountAlgebra table240 = counts240 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table239 row239 counts239 1284 counts239_eq (by decide +kernel)
def heights240 : Fin 240 → Nat := extend heights239 16
theorem heights240_eq : Table.fold (fun _ => 0) heightAlgebra table240 = heights240 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table239 row239 heights239 16 heights239_eq (by decide +kernel)
def row240 : Row 240 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨222, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 240))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 240))) slot.1)
def table241 : Table 241 := .push table240 row240
def counts241 : Fin 241 → Nat := extend counts240 1284
theorem counts241_eq : Table.fold (fun _ => 1) nodeCountAlgebra table241 = counts241 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table240 row240 counts240 1284 counts240_eq (by decide +kernel)
def heights241 : Fin 241 → Nat := extend heights240 16
theorem heights241_eq : Table.fold (fun _ => 0) heightAlgebra table241 = heights241 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table240 row240 heights240 16 heights240_eq (by decide +kernel)
def row241 : Row 241 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨225, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 241))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 241))) slot.1)
def table242 : Table 242 := .push table241 row241
def counts242 : Fin 242 → Nat := extend counts241 1284
theorem counts242_eq : Table.fold (fun _ => 1) nodeCountAlgebra table242 = counts242 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table241 row241 counts241 1284 counts241_eq (by decide +kernel)
def heights242 : Fin 242 → Nat := extend heights241 16
theorem heights242_eq : Table.fold (fun _ => 0) heightAlgebra table242 = heights242 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table241 row241 heights241 16 heights241_eq (by decide +kernel)
def row242 : Row 242 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨209, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 242))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 242))) slot.1)
def table243 : Table 243 := .push table242 row242
def counts243 : Fin 243 → Nat := extend counts242 1284
theorem counts243_eq : Table.fold (fun _ => 1) nodeCountAlgebra table243 = counts243 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table242 row242 counts242 1284 counts242_eq (by decide +kernel)
def heights243 : Fin 243 → Nat := extend heights242 16
theorem heights243_eq : Table.fold (fun _ => 0) heightAlgebra table243 = heights243 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table242 row242 heights242 16 heights242_eq (by decide +kernel)
def row243 : Row 243 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨220, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 243))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 243))) slot.1)
def table244 : Table 244 := .push table243 row243
def counts244 : Fin 244 → Nat := extend counts243 1284
theorem counts244_eq : Table.fold (fun _ => 1) nodeCountAlgebra table244 = counts244 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table243 row243 counts243 1284 counts243_eq (by decide +kernel)
def heights244 : Fin 244 → Nat := extend heights243 16
theorem heights244_eq : Table.fold (fun _ => 0) heightAlgebra table244 = heights244 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table243 row243 heights243 16 heights243_eq (by decide +kernel)
def row244 : Row 244 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨221, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 244))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 244))) slot.1)
def table245 : Table 245 := .push table244 row244
def counts245 : Fin 245 → Nat := extend counts244 1284
theorem counts245_eq : Table.fold (fun _ => 1) nodeCountAlgebra table245 = counts245 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table244 row244 counts244 1284 counts244_eq (by decide +kernel)
def heights245 : Fin 245 → Nat := extend heights244 16
theorem heights245_eq : Table.fold (fun _ => 0) heightAlgebra table245 = heights245 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table244 row244 heights244 16 heights244_eq (by decide +kernel)
def row245 : Row 245 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨226, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 245))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 245))) slot.1)
def table246 : Table 246 := .push table245 row245
def counts246 : Fin 246 → Nat := extend counts245 1284
theorem counts246_eq : Table.fold (fun _ => 1) nodeCountAlgebra table246 = counts246 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table245 row245 counts245 1284 counts245_eq (by decide +kernel)
def heights246 : Fin 246 → Nat := extend heights245 16
theorem heights246_eq : Table.fold (fun _ => 0) heightAlgebra table246 = heights246 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table245 row245 heights245 16 heights245_eq (by decide +kernel)
def row246 : Row 246 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨212, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 246))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 246))) slot.1)
def table247 : Table 247 := .push table246 row246
def counts247 : Fin 247 → Nat := extend counts246 1284
theorem counts247_eq : Table.fold (fun _ => 1) nodeCountAlgebra table247 = counts247 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table246 row246 counts246 1284 counts246_eq (by decide +kernel)
def heights247 : Fin 247 → Nat := extend heights246 16
theorem heights247_eq : Table.fold (fun _ => 0) heightAlgebra table247 = heights247 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table246 row246 heights246 16 heights246_eq (by decide +kernel)
def row247 : Row 247 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨228, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 247))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 247))) slot.1)
def table248 : Table 248 := .push table247 row247
def counts248 : Fin 248 → Nat := extend counts247 1284
theorem counts248_eq : Table.fold (fun _ => 1) nodeCountAlgebra table248 = counts248 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table247 row247 counts247 1284 counts247_eq (by decide +kernel)
def heights248 : Fin 248 → Nat := extend heights247 16
theorem heights248_eq : Table.fold (fun _ => 0) heightAlgebra table248 = heights248 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table247 row247 heights247 16 heights247_eq (by decide +kernel)
def row248 : Row 248 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨234, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 248))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 248))) slot.1)
def table249 : Table 249 := .push table248 row248
def counts249 : Fin 249 → Nat := extend counts248 1284
theorem counts249_eq : Table.fold (fun _ => 1) nodeCountAlgebra table249 = counts249 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table248 row248 counts248 1284 counts248_eq (by decide +kernel)
def heights249 : Fin 249 → Nat := extend heights248 16
theorem heights249_eq : Table.fold (fun _ => 0) heightAlgebra table249 = heights249 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table248 row248 heights248 16 heights248_eq (by decide +kernel)
def row249 : Row 249 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨229, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 249))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 249))) slot.1)
def table250 : Table 250 := .push table249 row249
def counts250 : Fin 250 → Nat := extend counts249 1284
theorem counts250_eq : Table.fold (fun _ => 1) nodeCountAlgebra table250 = counts250 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table249 row249 counts249 1284 counts249_eq (by decide +kernel)
def heights250 : Fin 250 → Nat := extend heights249 16
theorem heights250_eq : Table.fold (fun _ => 0) heightAlgebra table250 = heights250 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table249 row249 heights249 16 heights249_eq (by decide +kernel)
def row250 : Row 250 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨231, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 250))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 250))) slot.1)
def table251 : Table 251 := .push table250 row250
def counts251 : Fin 251 → Nat := extend counts250 1284
theorem counts251_eq : Table.fold (fun _ => 1) nodeCountAlgebra table251 = counts251 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table250 row250 counts250 1284 counts250_eq (by decide +kernel)
def heights251 : Fin 251 → Nat := extend heights250 16
theorem heights251_eq : Table.fold (fun _ => 0) heightAlgebra table251 = heights251 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table250 row250 heights250 16 heights250_eq (by decide +kernel)
def row251 : Row 251 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨214, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 251))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 251))) slot.1)
def table252 : Table 252 := .push table251 row251
def counts252 : Fin 252 → Nat := extend counts251 1284
theorem counts252_eq : Table.fold (fun _ => 1) nodeCountAlgebra table252 = counts252 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table251 row251 counts251 1284 counts251_eq (by decide +kernel)
def heights252 : Fin 252 → Nat := extend heights251 16
theorem heights252_eq : Table.fold (fun _ => 0) heightAlgebra table252 = heights252 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table251 row251 heights251 16 heights251_eq (by decide +kernel)
def row252 : Row 252 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨219, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 252))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 252))) slot.1)
def table253 : Table 253 := .push table252 row252
def counts253 : Fin 253 → Nat := extend counts252 1284
theorem counts253_eq : Table.fold (fun _ => 1) nodeCountAlgebra table253 = counts253 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table252 row252 counts252 1284 counts252_eq (by decide +kernel)
def heights253 : Fin 253 → Nat := extend heights252 16
theorem heights253_eq : Table.fold (fun _ => 0) heightAlgebra table253 = heights253 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table252 row252 heights252 16 heights252_eq (by decide +kernel)
def row253 : Row 253 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨235, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 253))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 253))) slot.1)
def table254 : Table 254 := .push table253 row253
def counts254 : Fin 254 → Nat := extend counts253 1284
theorem counts254_eq : Table.fold (fun _ => 1) nodeCountAlgebra table254 = counts254 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table253 row253 counts253 1284 counts253_eq (by decide +kernel)
def heights254 : Fin 254 → Nat := extend heights253 16
theorem heights254_eq : Table.fold (fun _ => 0) heightAlgebra table254 = heights254 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table253 row253 heights253 16 heights253_eq (by decide +kernel)
def row254 : Row 254 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨218, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 254))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 254))) slot.1)
def table255 : Table 255 := .push table254 row254
def counts255 : Fin 255 → Nat := extend counts254 1284
theorem counts255_eq : Table.fold (fun _ => 1) nodeCountAlgebra table255 = counts255 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table254 row254 counts254 1284 counts254_eq (by decide +kernel)
def heights255 : Fin 255 → Nat := extend heights254 16
theorem heights255_eq : Table.fold (fun _ => 0) heightAlgebra table255 = heights255 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table254 row254 heights254 16 heights254_eq (by decide +kernel)
def row255 : Row 255 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨230, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 255))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 255))) slot.1)
def table256 : Table 256 := .push table255 row255
def counts256 : Fin 256 → Nat := extend counts255 1284
theorem counts256_eq : Table.fold (fun _ => 1) nodeCountAlgebra table256 = counts256 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table255 row255 counts255 1284 counts255_eq (by decide +kernel)
def heights256 : Fin 256 → Nat := extend heights255 16
theorem heights256_eq : Table.fold (fun _ => 0) heightAlgebra table256 = heights256 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table255 row255 heights255 16 heights255_eq (by decide +kernel)
def row256 : Row 256 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨216, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 256))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 256))) slot.1)
def table257 : Table 257 := .push table256 row256
def counts257 : Fin 257 → Nat := extend counts256 1284
theorem counts257_eq : Table.fold (fun _ => 1) nodeCountAlgebra table257 = counts257 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table256 row256 counts256 1284 counts256_eq (by decide +kernel)
def heights257 : Fin 257 → Nat := extend heights256 16
theorem heights257_eq : Table.fold (fun _ => 0) heightAlgebra table257 = heights257 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table256 row256 heights256 16 heights256_eq (by decide +kernel)
def row257 : Row 257 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨232, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 257))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 257))) slot.1)
def table258 : Table 258 := .push table257 row257
def counts258 : Fin 258 → Nat := extend counts257 1284
theorem counts258_eq : Table.fold (fun _ => 1) nodeCountAlgebra table258 = counts258 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table257 row257 counts257 1284 counts257_eq (by decide +kernel)
def heights258 : Fin 258 → Nat := extend heights257 16
theorem heights258_eq : Table.fold (fun _ => 0) heightAlgebra table258 = heights258 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table257 row257 heights257 16 heights257_eq (by decide +kernel)
def row258 : Row 258 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨213, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 258))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 258))) slot.1)
def table259 : Table 259 := .push table258 row258
def counts259 : Fin 259 → Nat := extend counts258 1284
theorem counts259_eq : Table.fold (fun _ => 1) nodeCountAlgebra table259 = counts259 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table258 row258 counts258 1284 counts258_eq (by decide +kernel)
def heights259 : Fin 259 → Nat := extend heights258 16
theorem heights259_eq : Table.fold (fun _ => 0) heightAlgebra table259 = heights259 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table258 row258 heights258 16 heights258_eq (by decide +kernel)
def row259 : Row 259 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨236, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 259))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 259))) slot.1)
def table260 : Table 260 := .push table259 row259
def counts260 : Fin 260 → Nat := extend counts259 1284
theorem counts260_eq : Table.fold (fun _ => 1) nodeCountAlgebra table260 = counts260 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table259 row259 counts259 1284 counts259_eq (by decide +kernel)
def heights260 : Fin 260 → Nat := extend heights259 16
theorem heights260_eq : Table.fold (fun _ => 0) heightAlgebra table260 = heights260 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table259 row259 heights259 16 heights259_eq (by decide +kernel)
def row260 : Row 260 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨211, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 260))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 260))) slot.1)
def table261 : Table 261 := .push table260 row260
def counts261 : Fin 261 → Nat := extend counts260 1284
theorem counts261_eq : Table.fold (fun _ => 1) nodeCountAlgebra table261 = counts261 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table260 row260 counts260 1284 counts260_eq (by decide +kernel)
def heights261 : Fin 261 → Nat := extend heights260 16
theorem heights261_eq : Table.fold (fun _ => 0) heightAlgebra table261 = heights261 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table260 row260 heights260 16 heights260_eq (by decide +kernel)
def row261 : Row 261 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨233, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 261))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 261))) slot.1)
def table262 : Table 262 := .push table261 row261
def counts262 : Fin 262 → Nat := extend counts261 1284
theorem counts262_eq : Table.fold (fun _ => 1) nodeCountAlgebra table262 = counts262 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table261 row261 counts261 1284 counts261_eq (by decide +kernel)
def heights262 : Fin 262 → Nat := extend heights261 16
theorem heights262_eq : Table.fold (fun _ => 0) heightAlgebra table262 = heights262 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table261 row261 heights261 16 heights261_eq (by decide +kernel)
def row262 : Row 262 := Row.node (Kind.vector 3) (List.get ([⟨223, by decide⟩, ⟨210, by decide⟩, ⟨217, by decide⟩] : List (Fin 262)))
def table263 : Table 263 := .push table262 row262
def counts263 : Fin 263 → Nat := extend counts262 5728
theorem counts263_eq : Table.fold (fun _ => 1) nodeCountAlgebra table263 = counts263 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table262 row262 counts262 5728 counts262_eq (by decide +kernel)
def heights263 : Fin 263 → Nat := extend heights262 16
theorem heights263_eq : Table.fold (fun _ => 0) heightAlgebra table263 = heights263 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table262 row262 heights262 16 heights262_eq (by decide +kernel)
def row263 : Row 263 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨237, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 263))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 263))) slot.1)
def table264 : Table 264 := .push table263 row263
def counts264 : Fin 264 → Nat := extend counts263 1284
theorem counts264_eq : Table.fold (fun _ => 1) nodeCountAlgebra table264 = counts264 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table263 row263 counts263 1284 counts263_eq (by decide +kernel)
def heights264 : Fin 264 → Nat := extend heights263 16
theorem heights264_eq : Table.fold (fun _ => 0) heightAlgebra table264 = heights264 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table263 row263 heights263 16 heights263_eq (by decide +kernel)
def row264 : Row 264 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨238, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 264))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 264))) slot.1)
def table265 : Table 265 := .push table264 row264
def counts265 : Fin 265 → Nat := extend counts264 1284
theorem counts265_eq : Table.fold (fun _ => 1) nodeCountAlgebra table265 = counts265 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table264 row264 counts264 1284 counts264_eq (by decide +kernel)
def heights265 : Fin 265 → Nat := extend heights264 16
theorem heights265_eq : Table.fold (fun _ => 0) heightAlgebra table265 = heights265 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table264 row264 heights264 16 heights264_eq (by decide +kernel)
def row265 : Row 265 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨227, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 265))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 265))) slot.1)
def table266 : Table 266 := .push table265 row265
def counts266 : Fin 266 → Nat := extend counts265 1284
theorem counts266_eq : Table.fold (fun _ => 1) nodeCountAlgebra table266 = counts266 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table265 row265 counts265 1284 counts265_eq (by decide +kernel)
def heights266 : Fin 266 → Nat := extend heights265 16
theorem heights266_eq : Table.fold (fun _ => 0) heightAlgebra table266 = heights266 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table265 row265 heights265 16 heights265_eq (by decide +kernel)
def row266 : Row 266 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨224, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 266))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 266))) slot.1)
def table267 : Table 267 := .push table266 row266
def counts267 : Fin 267 → Nat := extend counts266 1284
theorem counts267_eq : Table.fold (fun _ => 1) nodeCountAlgebra table267 = counts267 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table266 row266 counts266 1284 counts266_eq (by decide +kernel)
def heights267 : Fin 267 → Nat := extend heights266 16
theorem heights267_eq : Table.fold (fun _ => 0) heightAlgebra table267 = heights267 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table266 row266 heights266 16 heights266_eq (by decide +kernel)
def row267 : Row 267 := Row.node (Kind.vector 2) (List.get ([⟨249, by decide⟩, ⟨206, by decide⟩] : List (Fin 267)))
def table268 : Table 268 := .push table267 row267
def counts268 : Fin 268 → Nat := extend counts267 1921
theorem counts268_eq : Table.fold (fun _ => 1) nodeCountAlgebra table268 = counts268 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table267 row267 counts267 1921 counts267_eq (by decide +kernel)
def heights268 : Fin 268 → Nat := extend heights267 17
theorem heights268_eq : Table.fold (fun _ => 0) heightAlgebra table268 = heights268 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table267 row267 heights267 17 heights267_eq (by decide +kernel)
def row268 : Row 268 := Row.node (Kind.vector 2) (List.get ([⟨264, by decide⟩, ⟨208, by decide⟩] : List (Fin 268)))
def table269 : Table 269 := .push table268 row268
def counts269 : Fin 269 → Nat := extend counts268 1921
theorem counts269_eq : Table.fold (fun _ => 1) nodeCountAlgebra table269 = counts269 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table268 row268 counts268 1921 counts268_eq (by decide +kernel)
def heights269 : Fin 269 → Nat := extend heights268 17
theorem heights269_eq : Table.fold (fun _ => 0) heightAlgebra table269 = heights269 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table268 row268 heights268 17 heights268_eq (by decide +kernel)
def row269 : Row 269 := Row.node (Kind.vector 2) (List.get ([⟨251, by decide⟩, ⟨201, by decide⟩] : List (Fin 269)))
def table270 : Table 270 := .push table269 row269
def counts270 : Fin 270 → Nat := extend counts269 1921
theorem counts270_eq : Table.fold (fun _ => 1) nodeCountAlgebra table270 = counts270 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table269 row269 counts269 1921 counts269_eq (by decide +kernel)
def heights270 : Fin 270 → Nat := extend heights269 17
theorem heights270_eq : Table.fold (fun _ => 0) heightAlgebra table270 = heights270 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table269 row269 heights269 17 heights269_eq (by decide +kernel)
def row270 : Row 270 := Row.node (Kind.vector 2) (List.get ([⟨247, by decide⟩, ⟨205, by decide⟩] : List (Fin 270)))
def table271 : Table 271 := .push table270 row270
def counts271 : Fin 271 → Nat := extend counts270 1921
theorem counts271_eq : Table.fold (fun _ => 1) nodeCountAlgebra table271 = counts271 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table270 row270 counts270 1921 counts270_eq (by decide +kernel)
def heights271 : Fin 271 → Nat := extend heights270 17
theorem heights271_eq : Table.fold (fun _ => 0) heightAlgebra table271 = heights271 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table270 row270 heights270 17 heights270_eq (by decide +kernel)
def row271 : Row 271 := Row.node (Kind.vector 2) (List.get ([⟨259, by decide⟩, ⟨202, by decide⟩] : List (Fin 271)))
def table272 : Table 272 := .push table271 row271
def counts272 : Fin 272 → Nat := extend counts271 1921
theorem counts272_eq : Table.fold (fun _ => 1) nodeCountAlgebra table272 = counts272 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table271 row271 counts271 1921 counts271_eq (by decide +kernel)
def heights272 : Fin 272 → Nat := extend heights271 17
theorem heights272_eq : Table.fold (fun _ => 0) heightAlgebra table272 = heights272 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table271 row271 heights271 17 heights271_eq (by decide +kernel)
def row272 : Row 272 := Row.node (Kind.vector 2) (List.get ([⟨243, by decide⟩, ⟨200, by decide⟩] : List (Fin 272)))
def table273 : Table 273 := .push table272 row272
def counts273 : Fin 273 → Nat := extend counts272 1921
theorem counts273_eq : Table.fold (fun _ => 1) nodeCountAlgebra table273 = counts273 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table272 row272 counts272 1921 counts272_eq (by decide +kernel)
def heights273 : Fin 273 → Nat := extend heights272 17
theorem heights273_eq : Table.fold (fun _ => 0) heightAlgebra table273 = heights273 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table272 row272 heights272 17 heights272_eq (by decide +kernel)
def row273 : Row 273 := Row.node (Kind.vector 2) (List.get ([⟨250, by decide⟩, ⟨200, by decide⟩] : List (Fin 273)))
def table274 : Table 274 := .push table273 row273
def counts274 : Fin 274 → Nat := extend counts273 1921
theorem counts274_eq : Table.fold (fun _ => 1) nodeCountAlgebra table274 = counts274 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table273 row273 counts273 1921 counts273_eq (by decide +kernel)
def heights274 : Fin 274 → Nat := extend heights273 17
theorem heights274_eq : Table.fold (fun _ => 0) heightAlgebra table274 = heights274 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table273 row273 heights273 17 heights273_eq (by decide +kernel)
def row274 : Row 274 := Row.node (Kind.map 1) (fun (slot : Fin 1 × Bool) => if slot.2 then (List.get ([⟨262, by decide⟩] : List (Fin 274))) slot.1 else (List.get ([⟨63, by decide⟩] : List (Fin 274))) slot.1)
def table275 : Table 275 := .push table274 row274
def counts275 : Fin 275 → Nat := extend counts274 5730
theorem counts275_eq : Table.fold (fun _ => 1) nodeCountAlgebra table275 = counts275 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table274 row274 counts274 5730 counts274_eq (by decide +kernel)
def heights275 : Fin 275 → Nat := extend heights274 17
theorem heights275_eq : Table.fold (fun _ => 0) heightAlgebra table275 = heights275 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table274 row274 heights274 17 heights274_eq (by decide +kernel)
def row275 : Row 275 := Row.node (Kind.vector 2) (List.get ([⟨263, by decide⟩, ⟨203, by decide⟩] : List (Fin 275)))
def table276 : Table 276 := .push table275 row275
def counts276 : Fin 276 → Nat := extend counts275 1921
theorem counts276_eq : Table.fold (fun _ => 1) nodeCountAlgebra table276 = counts276 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table275 row275 counts275 1921 counts275_eq (by decide +kernel)
def heights276 : Fin 276 → Nat := extend heights275 17
theorem heights276_eq : Table.fold (fun _ => 0) heightAlgebra table276 = heights276 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table275 row275 heights275 17 heights275_eq (by decide +kernel)
def row276 : Row 276 := Row.node (Kind.vector 2) (List.get ([⟨258, by decide⟩, ⟨207, by decide⟩] : List (Fin 276)))
def table277 : Table 277 := .push table276 row276
def counts277 : Fin 277 → Nat := extend counts276 1921
theorem counts277_eq : Table.fold (fun _ => 1) nodeCountAlgebra table277 = counts277 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table276 row276 counts276 1921 counts276_eq (by decide +kernel)
def heights277 : Fin 277 → Nat := extend heights276 17
theorem heights277_eq : Table.fold (fun _ => 0) heightAlgebra table277 = heights277 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table276 row276 heights276 17 heights276_eq (by decide +kernel)
def row277 : Row 277 := Row.node (Kind.vector 2) (List.get ([⟨246, by decide⟩, ⟨204, by decide⟩] : List (Fin 277)))
def table278 : Table 278 := .push table277 row277
def counts278 : Fin 278 → Nat := extend counts277 1921
theorem counts278_eq : Table.fold (fun _ => 1) nodeCountAlgebra table278 = counts278 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table277 row277 counts277 1921 counts277_eq (by decide +kernel)
def heights278 : Fin 278 → Nat := extend heights277 17
theorem heights278_eq : Table.fold (fun _ => 0) heightAlgebra table278 = heights278 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table277 row277 heights277 17 heights277_eq (by decide +kernel)
def row278 : Row 278 := Row.node (Kind.vector 2) (List.get ([⟨244, by decide⟩, ⟨200, by decide⟩] : List (Fin 278)))
def table279 : Table 279 := .push table278 row278
def counts279 : Fin 279 → Nat := extend counts278 1921
theorem counts279_eq : Table.fold (fun _ => 1) nodeCountAlgebra table279 = counts279 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table278 row278 counts278 1921 counts278_eq (by decide +kernel)
def heights279 : Fin 279 → Nat := extend heights278 17
theorem heights279_eq : Table.fold (fun _ => 0) heightAlgebra table279 = heights279 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table278 row278 heights278 17 heights278_eq (by decide +kernel)
def row279 : Row 279 := Row.node (Kind.vector 2) (List.get ([⟨266, by decide⟩, ⟨205, by decide⟩] : List (Fin 279)))
def table280 : Table 280 := .push table279 row279
def counts280 : Fin 280 → Nat := extend counts279 1921
theorem counts280_eq : Table.fold (fun _ => 1) nodeCountAlgebra table280 = counts280 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table279 row279 counts279 1921 counts279_eq (by decide +kernel)
def heights280 : Fin 280 → Nat := extend heights279 17
theorem heights280_eq : Table.fold (fun _ => 0) heightAlgebra table280 = heights280 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table279 row279 heights279 17 heights279_eq (by decide +kernel)
def row280 : Row 280 := Row.node (Kind.vector 2) (List.get ([⟨241, by decide⟩, ⟨204, by decide⟩] : List (Fin 280)))
def table281 : Table 281 := .push table280 row280
def counts281 : Fin 281 → Nat := extend counts280 1921
theorem counts281_eq : Table.fold (fun _ => 1) nodeCountAlgebra table281 = counts281 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table280 row280 counts280 1921 counts280_eq (by decide +kernel)
def heights281 : Fin 281 → Nat := extend heights280 17
theorem heights281_eq : Table.fold (fun _ => 0) heightAlgebra table281 = heights281 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table280 row280 heights280 17 heights280_eq (by decide +kernel)
def row281 : Row 281 := Row.node (Kind.vector 2) (List.get ([⟨245, by decide⟩, ⟨204, by decide⟩] : List (Fin 281)))
def table282 : Table 282 := .push table281 row281
def counts282 : Fin 282 → Nat := extend counts281 1921
theorem counts282_eq : Table.fold (fun _ => 1) nodeCountAlgebra table282 = counts282 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table281 row281 counts281 1921 counts281_eq (by decide +kernel)
def heights282 : Fin 282 → Nat := extend heights281 17
theorem heights282_eq : Table.fold (fun _ => 0) heightAlgebra table282 = heights282 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table281 row281 heights281 17 heights281_eq (by decide +kernel)
def row282 : Row 282 := Row.node (Kind.vector 2) (List.get ([⟨257, by decide⟩, ⟨203, by decide⟩] : List (Fin 282)))
def table283 : Table 283 := .push table282 row282
def counts283 : Fin 283 → Nat := extend counts282 1921
theorem counts283_eq : Table.fold (fun _ => 1) nodeCountAlgebra table283 = counts283 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table282 row282 counts282 1921 counts282_eq (by decide +kernel)
def heights283 : Fin 283 → Nat := extend heights282 17
theorem heights283_eq : Table.fold (fun _ => 0) heightAlgebra table283 = heights283 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table282 row282 heights282 17 heights282_eq (by decide +kernel)
def row283 : Row 283 := Row.node (Kind.vector 2) (List.get ([⟨255, by decide⟩, ⟨207, by decide⟩] : List (Fin 283)))
def table284 : Table 284 := .push table283 row283
def counts284 : Fin 284 → Nat := extend counts283 1921
theorem counts284_eq : Table.fold (fun _ => 1) nodeCountAlgebra table284 = counts284 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table283 row283 counts283 1921 counts283_eq (by decide +kernel)
def heights284 : Fin 284 → Nat := extend heights283 17
theorem heights284_eq : Table.fold (fun _ => 0) heightAlgebra table284 = heights284 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table283 row283 heights283 17 heights283_eq (by decide +kernel)
def row284 : Row 284 := Row.node (Kind.vector 2) (List.get ([⟨260, by decide⟩, ⟨208, by decide⟩] : List (Fin 284)))
def table285 : Table 285 := .push table284 row284
def counts285 : Fin 285 → Nat := extend counts284 1921
theorem counts285_eq : Table.fold (fun _ => 1) nodeCountAlgebra table285 = counts285 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table284 row284 counts284 1921 counts284_eq (by decide +kernel)
def heights285 : Fin 285 → Nat := extend heights284 17
theorem heights285_eq : Table.fold (fun _ => 0) heightAlgebra table285 = heights285 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table284 row284 heights284 17 heights284_eq (by decide +kernel)
def row285 : Row 285 := Row.node (Kind.vector 2) (List.get ([⟨265, by decide⟩, ⟨201, by decide⟩] : List (Fin 285)))
def table286 : Table 286 := .push table285 row285
def counts286 : Fin 286 → Nat := extend counts285 1921
theorem counts286_eq : Table.fold (fun _ => 1) nodeCountAlgebra table286 = counts286 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table285 row285 counts285 1921 counts285_eq (by decide +kernel)
def heights286 : Fin 286 → Nat := extend heights285 17
theorem heights286_eq : Table.fold (fun _ => 0) heightAlgebra table286 = heights286 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table285 row285 heights285 17 heights285_eq (by decide +kernel)
def row286 : Row 286 := Row.node (Kind.vector 2) (List.get ([⟨240, by decide⟩, ⟨208, by decide⟩] : List (Fin 286)))
def table287 : Table 287 := .push table286 row286
def counts287 : Fin 287 → Nat := extend counts286 1921
theorem counts287_eq : Table.fold (fun _ => 1) nodeCountAlgebra table287 = counts287 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table286 row286 counts286 1921 counts286_eq (by decide +kernel)
def heights287 : Fin 287 → Nat := extend heights286 17
theorem heights287_eq : Table.fold (fun _ => 0) heightAlgebra table287 = heights287 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table286 row286 heights286 17 heights286_eq (by decide +kernel)
def row287 : Row 287 := Row.node (Kind.vector 2) (List.get ([⟨248, by decide⟩, ⟨201, by decide⟩] : List (Fin 287)))
def table288 : Table 288 := .push table287 row287
def counts288 : Fin 288 → Nat := extend counts287 1921
theorem counts288_eq : Table.fold (fun _ => 1) nodeCountAlgebra table288 = counts288 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table287 row287 counts287 1921 counts287_eq (by decide +kernel)
def heights288 : Fin 288 → Nat := extend heights287 17
theorem heights288_eq : Table.fold (fun _ => 0) heightAlgebra table288 = heights288 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table287 row287 heights287 17 heights287_eq (by decide +kernel)
def row288 : Row 288 := Row.node (Kind.vector 2) (List.get ([⟨254, by decide⟩, ⟨206, by decide⟩] : List (Fin 288)))
def table289 : Table 289 := .push table288 row288
def counts289 : Fin 289 → Nat := extend counts288 1921
theorem counts289_eq : Table.fold (fun _ => 1) nodeCountAlgebra table289 = counts289 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table288 row288 counts288 1921 counts288_eq (by decide +kernel)
def heights289 : Fin 289 → Nat := extend heights288 17
theorem heights289_eq : Table.fold (fun _ => 0) heightAlgebra table289 = heights289 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table288 row288 heights288 17 heights288_eq (by decide +kernel)
def row289 : Row 289 := Row.node (Kind.vector 2) (List.get ([⟨256, by decide⟩, ⟨207, by decide⟩] : List (Fin 289)))
def table290 : Table 290 := .push table289 row289
def counts290 : Fin 290 → Nat := extend counts289 1921
theorem counts290_eq : Table.fold (fun _ => 1) nodeCountAlgebra table290 = counts290 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table289 row289 counts289 1921 counts289_eq (by decide +kernel)
def heights290 : Fin 290 → Nat := extend heights289 17
theorem heights290_eq : Table.fold (fun _ => 0) heightAlgebra table290 = heights290 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table289 row289 heights289 17 heights289_eq (by decide +kernel)
def row290 : Row 290 := Row.node (Kind.vector 2) (List.get ([⟨242, by decide⟩, ⟨203, by decide⟩] : List (Fin 290)))
def table291 : Table 291 := .push table290 row290
def counts291 : Fin 291 → Nat := extend counts290 1921
theorem counts291_eq : Table.fold (fun _ => 1) nodeCountAlgebra table291 = counts291 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table290 row290 counts290 1921 counts290_eq (by decide +kernel)
def heights291 : Fin 291 → Nat := extend heights290 17
theorem heights291_eq : Table.fold (fun _ => 0) heightAlgebra table291 = heights291 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table290 row290 heights290 17 heights290_eq (by decide +kernel)
def row291 : Row 291 := Row.node (Kind.vector 2) (List.get ([⟨253, by decide⟩, ⟨206, by decide⟩] : List (Fin 291)))
def table292 : Table 292 := .push table291 row291
def counts292 : Fin 292 → Nat := extend counts291 1921
theorem counts292_eq : Table.fold (fun _ => 1) nodeCountAlgebra table292 = counts292 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table291 row291 counts291 1921 counts291_eq (by decide +kernel)
def heights292 : Fin 292 → Nat := extend heights291 17
theorem heights292_eq : Table.fold (fun _ => 0) heightAlgebra table292 = heights292 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table291 row291 heights291 17 heights291_eq (by decide +kernel)
def row292 : Row 292 := Row.node (Kind.vector 2) (List.get ([⟨261, by decide⟩, ⟨202, by decide⟩] : List (Fin 292)))
def table293 : Table 293 := .push table292 row292
def counts293 : Fin 293 → Nat := extend counts292 1921
theorem counts293_eq : Table.fold (fun _ => 1) nodeCountAlgebra table293 = counts293 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table292 row292 counts292 1921 counts292_eq (by decide +kernel)
def heights293 : Fin 293 → Nat := extend heights292 17
theorem heights293_eq : Table.fold (fun _ => 0) heightAlgebra table293 = heights293 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table292 row292 heights292 17 heights292_eq (by decide +kernel)
def row293 : Row 293 := Row.node (Kind.vector 2) (List.get ([⟨252, by decide⟩, ⟨205, by decide⟩] : List (Fin 293)))
def table294 : Table 294 := .push table293 row293
def counts294 : Fin 294 → Nat := extend counts293 1921
theorem counts294_eq : Table.fold (fun _ => 1) nodeCountAlgebra table294 = counts294 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table293 row293 counts293 1921 counts293_eq (by decide +kernel)
def heights294 : Fin 294 → Nat := extend heights293 17
theorem heights294_eq : Table.fold (fun _ => 0) heightAlgebra table294 = heights294 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table293 row293 heights293 17 heights293_eq (by decide +kernel)
def row294 : Row 294 := Row.node (Kind.vector 2) (List.get ([⟨239, by decide⟩, ⟨202, by decide⟩] : List (Fin 294)))
def table295 : Table 295 := .push table294 row294
def counts295 : Fin 295 → Nat := extend counts294 1921
theorem counts295_eq : Table.fold (fun _ => 1) nodeCountAlgebra table295 = counts295 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table294 row294 counts294 1921 counts294_eq (by decide +kernel)
def heights295 : Fin 295 → Nat := extend heights294 17
theorem heights295_eq : Table.fold (fun _ => 0) heightAlgebra table295 = heights295 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table294 row294 heights294 17 heights294_eq (by decide +kernel)
def row295 : Row 295 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨282, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 295))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 295))) slot.1)
def table296 : Table 296 := .push table295 row295
def counts296 : Fin 296 → Nat := extend counts295 1932
theorem counts296_eq : Table.fold (fun _ => 1) nodeCountAlgebra table296 = counts296 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table295 row295 counts295 1932 counts295_eq (by decide +kernel)
def heights296 : Fin 296 → Nat := extend heights295 18
theorem heights296_eq : Table.fold (fun _ => 0) heightAlgebra table296 = heights296 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table295 row295 heights295 18 heights295_eq (by decide +kernel)
def row296 : Row 296 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨267, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 296))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 296))) slot.1)
def table297 : Table 297 := .push table296 row296
def counts297 : Fin 297 → Nat := extend counts296 1932
theorem counts297_eq : Table.fold (fun _ => 1) nodeCountAlgebra table297 = counts297 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table296 row296 counts296 1932 counts296_eq (by decide +kernel)
def heights297 : Fin 297 → Nat := extend heights296 18
theorem heights297_eq : Table.fold (fun _ => 0) heightAlgebra table297 = heights297 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table296 row296 heights296 18 heights296_eq (by decide +kernel)
def row297 : Row 297 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨275, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 297))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 297))) slot.1)
def table298 : Table 298 := .push table297 row297
def counts298 : Fin 298 → Nat := extend counts297 1932
theorem counts298_eq : Table.fold (fun _ => 1) nodeCountAlgebra table298 = counts298 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table297 row297 counts297 1932 counts297_eq (by decide +kernel)
def heights298 : Fin 298 → Nat := extend heights297 18
theorem heights298_eq : Table.fold (fun _ => 0) heightAlgebra table298 = heights298 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table297 row297 heights297 18 heights297_eq (by decide +kernel)
def row298 : Row 298 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨281, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 298))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 298))) slot.1)
def table299 : Table 299 := .push table298 row298
def counts299 : Fin 299 → Nat := extend counts298 1932
theorem counts299_eq : Table.fold (fun _ => 1) nodeCountAlgebra table299 = counts299 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table298 row298 counts298 1932 counts298_eq (by decide +kernel)
def heights299 : Fin 299 → Nat := extend heights298 18
theorem heights299_eq : Table.fold (fun _ => 0) heightAlgebra table299 = heights299 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table298 row298 heights298 18 heights298_eq (by decide +kernel)
def row299 : Row 299 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨270, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 299))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 299))) slot.1)
def table300 : Table 300 := .push table299 row299
def counts300 : Fin 300 → Nat := extend counts299 1932
theorem counts300_eq : Table.fold (fun _ => 1) nodeCountAlgebra table300 = counts300 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table299 row299 counts299 1932 counts299_eq (by decide +kernel)
def heights300 : Fin 300 → Nat := extend heights299 18
theorem heights300_eq : Table.fold (fun _ => 0) heightAlgebra table300 = heights300 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table299 row299 heights299 18 heights299_eq (by decide +kernel)
def row300 : Row 300 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨290, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 300))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 300))) slot.1)
def table301 : Table 301 := .push table300 row300
def counts301 : Fin 301 → Nat := extend counts300 1932
theorem counts301_eq : Table.fold (fun _ => 1) nodeCountAlgebra table301 = counts301 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table300 row300 counts300 1932 counts300_eq (by decide +kernel)
def heights301 : Fin 301 → Nat := extend heights300 18
theorem heights301_eq : Table.fold (fun _ => 0) heightAlgebra table301 = heights301 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table300 row300 heights300 18 heights300_eq (by decide +kernel)
def row301 : Row 301 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨277, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 301))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 301))) slot.1)
def table302 : Table 302 := .push table301 row301
def counts302 : Fin 302 → Nat := extend counts301 1932
theorem counts302_eq : Table.fold (fun _ => 1) nodeCountAlgebra table302 = counts302 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table301 row301 counts301 1932 counts301_eq (by decide +kernel)
def heights302 : Fin 302 → Nat := extend heights301 18
theorem heights302_eq : Table.fold (fun _ => 0) heightAlgebra table302 = heights302 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table301 row301 heights301 18 heights301_eq (by decide +kernel)
def row302 : Row 302 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨292, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 302))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 302))) slot.1)
def table303 : Table 303 := .push table302 row302
def counts303 : Fin 303 → Nat := extend counts302 1932
theorem counts303_eq : Table.fold (fun _ => 1) nodeCountAlgebra table303 = counts303 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table302 row302 counts302 1932 counts302_eq (by decide +kernel)
def heights303 : Fin 303 → Nat := extend heights302 18
theorem heights303_eq : Table.fold (fun _ => 0) heightAlgebra table303 = heights303 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table302 row302 heights302 18 heights302_eq (by decide +kernel)
def row303 : Row 303 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨278, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 303))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 303))) slot.1)
def table304 : Table 304 := .push table303 row303
def counts304 : Fin 304 → Nat := extend counts303 1932
theorem counts304_eq : Table.fold (fun _ => 1) nodeCountAlgebra table304 = counts304 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table303 row303 counts303 1932 counts303_eq (by decide +kernel)
def heights304 : Fin 304 → Nat := extend heights303 18
theorem heights304_eq : Table.fold (fun _ => 0) heightAlgebra table304 = heights304 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table303 row303 heights303 18 heights303_eq (by decide +kernel)
def row304 : Row 304 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨285, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 304))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 304))) slot.1)
def table305 : Table 305 := .push table304 row304
def counts305 : Fin 305 → Nat := extend counts304 1932
theorem counts305_eq : Table.fold (fun _ => 1) nodeCountAlgebra table305 = counts305 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table304 row304 counts304 1932 counts304_eq (by decide +kernel)
def heights305 : Fin 305 → Nat := extend heights304 18
theorem heights305_eq : Table.fold (fun _ => 0) heightAlgebra table305 = heights305 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table304 row304 heights304 18 heights304_eq (by decide +kernel)
def row305 : Row 305 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨272, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 305))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 305))) slot.1)
def table306 : Table 306 := .push table305 row305
def counts306 : Fin 306 → Nat := extend counts305 1932
theorem counts306_eq : Table.fold (fun _ => 1) nodeCountAlgebra table306 = counts306 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table305 row305 counts305 1932 counts305_eq (by decide +kernel)
def heights306 : Fin 306 → Nat := extend heights305 18
theorem heights306_eq : Table.fold (fun _ => 0) heightAlgebra table306 = heights306 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table305 row305 heights305 18 heights305_eq (by decide +kernel)
def row306 : Row 306 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨271, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 306))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 306))) slot.1)
def table307 : Table 307 := .push table306 row306
def counts307 : Fin 307 → Nat := extend counts306 1932
theorem counts307_eq : Table.fold (fun _ => 1) nodeCountAlgebra table307 = counts307 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table306 row306 counts306 1932 counts306_eq (by decide +kernel)
def heights307 : Fin 307 → Nat := extend heights306 18
theorem heights307_eq : Table.fold (fun _ => 0) heightAlgebra table307 = heights307 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table306 row306 heights306 18 heights306_eq (by decide +kernel)
def row307 : Row 307 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨289, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 307))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 307))) slot.1)
def table308 : Table 308 := .push table307 row307
def counts308 : Fin 308 → Nat := extend counts307 1932
theorem counts308_eq : Table.fold (fun _ => 1) nodeCountAlgebra table308 = counts308 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table307 row307 counts307 1932 counts307_eq (by decide +kernel)
def heights308 : Fin 308 → Nat := extend heights307 18
theorem heights308_eq : Table.fold (fun _ => 0) heightAlgebra table308 = heights308 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table307 row307 heights307 18 heights307_eq (by decide +kernel)
def row308 : Row 308 := Row.node (Kind.map 8) (fun (slot : Fin 8 × Bool) => if slot.2 then (List.get ([⟨274, by decide⟩, ⟨35, by decide⟩, ⟨14, by decide⟩, ⟨78, by decide⟩, ⟨48, by decide⟩, ⟨86, by decide⟩, ⟨105, by decide⟩, ⟨105, by decide⟩] : List (Fin 308))) slot.1 else (List.get ([⟨5, by decide⟩, ⟨7, by decide⟩, ⟨36, by decide⟩, ⟨39, by decide⟩, ⟨40, by decide⟩, ⟨43, by decide⟩, ⟨52, by decide⟩, ⟨53, by decide⟩] : List (Fin 308))) slot.1)
def table309 : Table 309 := .push table308 row308
def counts309 : Fin 309 → Nat := extend counts308 5808
theorem counts309_eq : Table.fold (fun _ => 1) nodeCountAlgebra table309 = counts309 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table308 row308 counts308 5808 counts308_eq (by decide +kernel)
def heights309 : Fin 309 → Nat := extend heights308 18
theorem heights309_eq : Table.fold (fun _ => 0) heightAlgebra table309 = heights309 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table308 row308 heights308 18 heights308_eq (by decide +kernel)
def row309 : Row 309 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨283, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 309))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 309))) slot.1)
def table310 : Table 310 := .push table309 row309
def counts310 : Fin 310 → Nat := extend counts309 1932
theorem counts310_eq : Table.fold (fun _ => 1) nodeCountAlgebra table310 = counts310 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table309 row309 counts309 1932 counts309_eq (by decide +kernel)
def heights310 : Fin 310 → Nat := extend heights309 18
theorem heights310_eq : Table.fold (fun _ => 0) heightAlgebra table310 = heights310 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table309 row309 heights309 18 heights309_eq (by decide +kernel)
def row310 : Row 310 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨291, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 310))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 310))) slot.1)
def table311 : Table 311 := .push table310 row310
def counts311 : Fin 311 → Nat := extend counts310 1932
theorem counts311_eq : Table.fold (fun _ => 1) nodeCountAlgebra table311 = counts311 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table310 row310 counts310 1932 counts310_eq (by decide +kernel)
def heights311 : Fin 311 → Nat := extend heights310 18
theorem heights311_eq : Table.fold (fun _ => 0) heightAlgebra table311 = heights311 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table310 row310 heights310 18 heights310_eq (by decide +kernel)
def row311 : Row 311 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨273, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 311))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 311))) slot.1)
def table312 : Table 312 := .push table311 row311
def counts312 : Fin 312 → Nat := extend counts311 1932
theorem counts312_eq : Table.fold (fun _ => 1) nodeCountAlgebra table312 = counts312 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table311 row311 counts311 1932 counts311_eq (by decide +kernel)
def heights312 : Fin 312 → Nat := extend heights311 18
theorem heights312_eq : Table.fold (fun _ => 0) heightAlgebra table312 = heights312 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table311 row311 heights311 18 heights311_eq (by decide +kernel)
def row312 : Row 312 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨269, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 312))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 312))) slot.1)
def table313 : Table 313 := .push table312 row312
def counts313 : Fin 313 → Nat := extend counts312 1932
theorem counts313_eq : Table.fold (fun _ => 1) nodeCountAlgebra table313 = counts313 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table312 row312 counts312 1932 counts312_eq (by decide +kernel)
def heights313 : Fin 313 → Nat := extend heights312 18
theorem heights313_eq : Table.fold (fun _ => 0) heightAlgebra table313 = heights313 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table312 row312 heights312 18 heights312_eq (by decide +kernel)
def row313 : Row 313 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨268, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 313))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 313))) slot.1)
def table314 : Table 314 := .push table313 row313
def counts314 : Fin 314 → Nat := extend counts313 1932
theorem counts314_eq : Table.fold (fun _ => 1) nodeCountAlgebra table314 = counts314 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table313 row313 counts313 1932 counts313_eq (by decide +kernel)
def heights314 : Fin 314 → Nat := extend heights313 18
theorem heights314_eq : Table.fold (fun _ => 0) heightAlgebra table314 = heights314 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table313 row313 heights313 18 heights313_eq (by decide +kernel)
def row314 : Row 314 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨280, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 314))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 314))) slot.1)
def table315 : Table 315 := .push table314 row314
def counts315 : Fin 315 → Nat := extend counts314 1932
theorem counts315_eq : Table.fold (fun _ => 1) nodeCountAlgebra table315 = counts315 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table314 row314 counts314 1932 counts314_eq (by decide +kernel)
def heights315 : Fin 315 → Nat := extend heights314 18
theorem heights315_eq : Table.fold (fun _ => 0) heightAlgebra table315 = heights315 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table314 row314 heights314 18 heights314_eq (by decide +kernel)
def row315 : Row 315 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨279, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 315))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 315))) slot.1)
def table316 : Table 316 := .push table315 row315
def counts316 : Fin 316 → Nat := extend counts315 1932
theorem counts316_eq : Table.fold (fun _ => 1) nodeCountAlgebra table316 = counts316 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table315 row315 counts315 1932 counts315_eq (by decide +kernel)
def heights316 : Fin 316 → Nat := extend heights315 18
theorem heights316_eq : Table.fold (fun _ => 0) heightAlgebra table316 = heights316 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table315 row315 heights315 18 heights315_eq (by decide +kernel)
def row316 : Row 316 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨287, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 316))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 316))) slot.1)
def table317 : Table 317 := .push table316 row316
def counts317 : Fin 317 → Nat := extend counts316 1932
theorem counts317_eq : Table.fold (fun _ => 1) nodeCountAlgebra table317 = counts317 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table316 row316 counts316 1932 counts316_eq (by decide +kernel)
def heights317 : Fin 317 → Nat := extend heights316 18
theorem heights317_eq : Table.fold (fun _ => 0) heightAlgebra table317 = heights317 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table316 row316 heights316 18 heights316_eq (by decide +kernel)
def row317 : Row 317 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨294, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 317))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 317))) slot.1)
def table318 : Table 318 := .push table317 row317
def counts318 : Fin 318 → Nat := extend counts317 1932
theorem counts318_eq : Table.fold (fun _ => 1) nodeCountAlgebra table318 = counts318 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table317 row317 counts317 1932 counts317_eq (by decide +kernel)
def heights318 : Fin 318 → Nat := extend heights317 18
theorem heights318_eq : Table.fold (fun _ => 0) heightAlgebra table318 = heights318 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table317 row317 heights317 18 heights317_eq (by decide +kernel)
def row318 : Row 318 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨288, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 318))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 318))) slot.1)
def table319 : Table 319 := .push table318 row318
def counts319 : Fin 319 → Nat := extend counts318 1932
theorem counts319_eq : Table.fold (fun _ => 1) nodeCountAlgebra table319 = counts319 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table318 row318 counts318 1932 counts318_eq (by decide +kernel)
def heights319 : Fin 319 → Nat := extend heights318 18
theorem heights319_eq : Table.fold (fun _ => 0) heightAlgebra table319 = heights319 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table318 row318 heights318 18 heights318_eq (by decide +kernel)
def row319 : Row 319 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨293, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 319))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 319))) slot.1)
def table320 : Table 320 := .push table319 row319
def counts320 : Fin 320 → Nat := extend counts319 1932
theorem counts320_eq : Table.fold (fun _ => 1) nodeCountAlgebra table320 = counts320 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table319 row319 counts319 1932 counts319_eq (by decide +kernel)
def heights320 : Fin 320 → Nat := extend heights319 18
theorem heights320_eq : Table.fold (fun _ => 0) heightAlgebra table320 = heights320 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table319 row319 heights319 18 heights319_eq (by decide +kernel)
def row320 : Row 320 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨286, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 320))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 320))) slot.1)
def table321 : Table 321 := .push table320 row320
def counts321 : Fin 321 → Nat := extend counts320 1932
theorem counts321_eq : Table.fold (fun _ => 1) nodeCountAlgebra table321 = counts321 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table320 row320 counts320 1932 counts320_eq (by decide +kernel)
def heights321 : Fin 321 → Nat := extend heights320 18
theorem heights321_eq : Table.fold (fun _ => 0) heightAlgebra table321 = heights321 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table320 row320 heights320 18 heights320_eq (by decide +kernel)
def row321 : Row 321 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨284, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 321))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 321))) slot.1)
def table322 : Table 322 := .push table321 row321
def counts322 : Fin 322 → Nat := extend counts321 1932
theorem counts322_eq : Table.fold (fun _ => 1) nodeCountAlgebra table322 = counts322 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table321 row321 counts321 1932 counts321_eq (by decide +kernel)
def heights322 : Fin 322 → Nat := extend heights321 18
theorem heights322_eq : Table.fold (fun _ => 0) heightAlgebra table322 = heights322 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table321 row321 heights321 18 heights321_eq (by decide +kernel)
def row322 : Row 322 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨276, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨66, by decide⟩] : List (Fin 322))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 322))) slot.1)
def table323 : Table 323 := .push table322 row322
def counts323 : Fin 323 → Nat := extend counts322 1932
theorem counts323_eq : Table.fold (fun _ => 1) nodeCountAlgebra table323 = counts323 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table322 row322 counts322 1932 counts322_eq (by decide +kernel)
def heights323 : Fin 323 → Nat := extend heights322 18
theorem heights323_eq : Table.fold (fun _ => 0) heightAlgebra table323 = heights323 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table322 row322 heights322 18 heights322_eq (by decide +kernel)
def row323 : Row 323 := Row.node (Kind.map 2) (fun (slot : Fin 2 × Bool) => if slot.2 then (List.get ([⟨308, by decide⟩, ⟨134, by decide⟩] : List (Fin 323))) slot.1 else (List.get ([⟨16, by decide⟩, ⟨58, by decide⟩] : List (Fin 323))) slot.1)
def table324 : Table 324 := .push table323 row323
def counts324 : Fin 324 → Nat := extend counts323 5979
theorem counts324_eq : Table.fold (fun _ => 1) nodeCountAlgebra table324 = counts324 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table323 row323 counts323 5979 counts323_eq (by decide +kernel)
def heights324 : Fin 324 → Nat := extend heights323 19
theorem heights324_eq : Table.fold (fun _ => 0) heightAlgebra table324 = heights324 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table323 row323 heights323 19 heights323_eq (by decide +kernel)
def row324 : Row 324 := Row.node (Kind.vector 27) (List.get ([⟨321, by decide⟩, ⟨301, by decide⟩, ⟨303, by decide⟩, ⟨320, by decide⟩, ⟨298, by decide⟩, ⟨305, by decide⟩, ⟨313, by decide⟩, ⟨314, by decide⟩, ⟨311, by decide⟩, ⟨295, by decide⟩, ⟨304, by decide⟩, ⟨315, by decide⟩, ⟨297, by decide⟩, ⟨312, by decide⟩, ⟨299, by decide⟩, ⟨300, by decide⟩, ⟨316, by decide⟩, ⟨319, by decide⟩, ⟨322, by decide⟩, ⟨306, by decide⟩, ⟨310, by decide⟩, ⟨307, by decide⟩, ⟨317, by decide⟩, ⟨318, by decide⟩, ⟨309, by decide⟩, ⟨302, by decide⟩, ⟨296, by decide⟩] : List (Fin 324)))
def table325 : Table 325 := .push table324 row324
def counts325 : Fin 325 → Nat := extend counts324 52165
theorem counts325_eq : Table.fold (fun _ => 1) nodeCountAlgebra table325 = counts325 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table324 row324 counts324 52165 counts324_eq (by decide +kernel)
def heights325 : Fin 325 → Nat := extend heights324 19
theorem heights325_eq : Table.fold (fun _ => 0) heightAlgebra table325 = heights325 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table324 row324 heights324 19 heights324_eq (by decide +kernel)
def row325 : Row 325 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨324, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 325))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 325))) slot.1)
def table326 : Table 326 := .push table325 row325
def counts326 : Fin 326 → Nat := extend counts325 52176
theorem counts326_eq : Table.fold (fun _ => 1) nodeCountAlgebra table326 = counts326 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table325 row325 counts325 52176 counts325_eq (by decide +kernel)
def heights326 : Fin 326 → Nat := extend heights325 20
theorem heights326_eq : Table.fold (fun _ => 0) heightAlgebra table326 = heights326 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table325 row325 heights325 20 heights325_eq (by decide +kernel)
def row326 : Row 326 := Row.node (Kind.vector 2) (List.get ([⟨132, by decide⟩, ⟨325, by decide⟩] : List (Fin 326)))
def table327 : Table 327 := .push table326 row326
def counts327 : Fin 327 → Nat := extend counts326 52213
theorem counts327_eq : Table.fold (fun _ => 1) nodeCountAlgebra table327 = counts327 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table326 row326 counts326 52213 counts326_eq (by decide +kernel)
def heights327 : Fin 327 → Nat := extend heights326 21
theorem heights327_eq : Table.fold (fun _ => 0) heightAlgebra table327 = heights327 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table326 row326 heights326 21 heights326_eq (by decide +kernel)
def row327 : Row 327 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨326, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨56, by decide⟩] : List (Fin 327))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 327))) slot.1)
def table328 : Table 328 := .push table327 row327
def counts328 : Fin 328 → Nat := extend counts327 52224
theorem counts328_eq : Table.fold (fun _ => 1) nodeCountAlgebra table328 = counts328 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table327 row327 counts327 52224 counts327_eq (by decide +kernel)
def heights328 : Fin 328 → Nat := extend heights327 22
theorem heights328_eq : Table.fold (fun _ => 0) heightAlgebra table328 = heights328 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table327 row327 heights327 22 heights327_eq (by decide +kernel)
def row328 : Row 328 := Row.node (Kind.vector 1) (List.get ([⟨327, by decide⟩] : List (Fin 328)))
def table329 : Table 329 := .push table328 row328
def counts329 : Fin 329 → Nat := extend counts328 52225
theorem counts329_eq : Table.fold (fun _ => 1) nodeCountAlgebra table329 = counts329 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table328 row328 counts328 52225 counts328_eq (by decide +kernel)
def heights329 : Fin 329 → Nat := extend heights328 23
theorem heights329_eq : Table.fold (fun _ => 0) heightAlgebra table329 = heights329 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table328 row328 heights328 23 heights328_eq (by decide +kernel)
def row329 : Row 329 := Row.node (Kind.map 5) (fun (slot : Fin 5 × Bool) => if slot.2 then (List.get ([⟨14, by decide⟩, ⟨328, by decide⟩, ⟨71, by decide⟩, ⟨45, by decide⟩, ⟨17, by decide⟩] : List (Fin 329))) slot.1 else (List.get ([⟨9, by decide⟩, ⟨28, by decide⟩, ⟨41, by decide⟩, ⟨65, by decide⟩, ⟨67, by decide⟩] : List (Fin 329))) slot.1)
def table330 : Table 330 := .push table329 row329
def counts330 : Fin 330 → Nat := extend counts329 52236
theorem counts330_eq : Table.fold (fun _ => 1) nodeCountAlgebra table330 = counts330 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table329 row329 counts329 52236 counts329_eq (by decide +kernel)
def heights330 : Fin 330 → Nat := extend heights329 24
theorem heights330_eq : Table.fold (fun _ => 0) heightAlgebra table330 = heights330 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table329 row329 heights329 24 heights329_eq (by decide +kernel)
def row330 : Row 330 := Row.node (Kind.map 3) (fun (slot : Fin 3 × Bool) => if slot.2 then (List.get ([⟨329, by decide⟩, ⟨45, by decide⟩, ⟨37, by decide⟩] : List (Fin 330))) slot.1 else (List.get ([⟨6, by decide⟩, ⟨11, by decide⟩, ⟨15, by decide⟩] : List (Fin 330))) slot.1)
def table331 : Table 331 := .push table330 row330
def counts331 : Fin 331 → Nat := extend counts330 52242
theorem counts331_eq : Table.fold (fun _ => 1) nodeCountAlgebra table331 = counts331 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table330 row330 counts330 52242 counts330_eq (by decide +kernel)
def heights331 : Fin 331 → Nat := extend heights330 25
theorem heights331_eq : Table.fold (fun _ => 0) heightAlgebra table331 = heights331 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table330 row330 heights330 25 heights330_eq (by decide +kernel)
def row331 : Row 331 := Row.node (Kind.map 15) (fun (slot : Fin 15 × Bool) => if slot.2 then (List.get ([⟨72, by decide⟩, ⟨45, by decide⟩, ⟨49, by decide⟩, ⟨84, by decide⟩, ⟨327, by decide⟩, ⟨14, by decide⟩, ⟨78, by decide⟩, ⟨8, by decide⟩, ⟨146, by decide⟩, ⟨62, by decide⟩, ⟨45, by decide⟩, ⟨29, by decide⟩, ⟨323, by decide⟩, ⟨330, by decide⟩, ⟨38, by decide⟩] : List (Fin 331))) slot.1 else (List.get ([⟨10, by decide⟩, ⟨11, by decide⟩, ⟨19, by decide⟩, ⟨22, by decide⟩, ⟨31, by decide⟩, ⟨33, by decide⟩, ⟨39, by decide⟩, ⟨44, by decide⟩, ⟨47, by decide⟩, ⟨51, by decide⟩, ⟨57, by decide⟩, ⟨59, by decide⟩, ⟨60, by decide⟩, ⟨64, by decide⟩, ⟨68, by decide⟩] : List (Fin 331))) slot.1)
def table332 : Table 332 := .push table331 row331
def counts332 : Fin 332 → Nat := extend counts331 110551
theorem counts332_eq : Table.fold (fun _ => 1) nodeCountAlgebra table332 = counts332 := by
  exact fold_push_of_certified_prefix (fun _ => 1) nodeCountAlgebra table331 row331 counts331 110551 counts331_eq (by decide +kernel)
def heights332 : Fin 332 → Nat := extend heights331 26
theorem heights332_eq : Table.fold (fun _ => 0) heightAlgebra table332 = heights332 := by
  exact fold_push_of_certified_prefix (fun _ => 0) heightAlgebra table331 row331 heights331 26 heights331_eq (by decide +kernel)
theorem original_expanded_nodes : (interpret table332 ⟨331, by decide⟩).expandedNodes = 110551 := by
  exact (expanded_node_count_agrees table332 ⟨331, by decide⟩).trans ((congrFun counts332_eq ⟨331, by decide⟩).trans (by decide +kernel))
theorem original_depth : (interpret table332 ⟨331, by decide⟩).height = 26 := by
  exact (height_agrees table332 ⟨331, by decide⟩).trans ((congrFun heights332_eq ⟨331, by decide⟩).trans (by decide +kernel))
#print axioms original_expanded_nodes
#print axioms original_depth
end GraphInstance
