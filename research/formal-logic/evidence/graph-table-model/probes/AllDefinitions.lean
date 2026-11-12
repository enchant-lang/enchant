import GraphTable
set_option autoImplicit false
set_option maxRecDepth 100000
set_option maxHeartbeats 8000000
open FormalGraphTable
namespace GraphInstance
def table0 : Table 0 := .empty
def table1 : Table 1 := .push table0 (Row.scalar (Scalar.keyword [110, 111]))
def table2 : Table 2 := .push table1 (Row.scalar (Scalar.keyword [121, 101, 115]))
def table3 : Table 3 := .push table2 (Row.scalar (Scalar.float64 ⟨9223372036854775808, by decide⟩))
def table4 : Table 4 := .push table3 (Row.scalar (Scalar.boolean false))
def table5 : Table 5 := .push table4 (Row.scalar (Scalar.keyword [102, 108, 111, 97, 116, 105, 110, 103]))
def table6 : Table 6 := .push table5 (Row.scalar (Scalar.keyword [112, 111, 115, 105, 116, 105, 118, 101, 45, 122, 101, 114, 111]))
def table7 : Table 7 := .push table6 (Row.scalar (Scalar.integer (0)))
def table8 : Table 8 := .push table7 (Row.scalar (Scalar.integer (1)))
def table9 : Table 9 := .push table8 (Row.scalar (Scalar.symbol [109, 111, 100, 101, 108, 47, 110, 97, 109, 101]))
def table10 : Table 10 := .push table9 (Row.scalar (Scalar.boolean true))
def table11 : Table 11 := .push table10 (Row.scalar (Scalar.integer (-3)))
def table12 : Table 12 := .push table11 (Row.scalar (Scalar.bytes [0, 255, 128]))
def table13 : Table 13 := .push table12 (Row.scalar (Scalar.keyword [110, 101, 103, 97, 116, 105, 118, 101, 45, 122, 101, 114, 111]))
def table14 : Table 14 := .push table13 (Row.scalar (Scalar.keyword [105, 110, 116, 101, 103, 101, 114]))
def table15 : Table 15 := .push table14 (Row.scalar (Scalar.float64 ⟨0, by decide⟩))
def table16 : Table 16 := .push table15 (Row.scalar (Scalar.nil))
def table17 : Table 17 := .push table16 (Row.scalar (Scalar.float64 ⟨4607182418800017408, by decide⟩))
def table18 : Table 18 := .push table17 (Row.scalar (Scalar.keyword [111, 107]))
def table19 : Table 19 := .push table18 (Row.scalar (Scalar.keyword [114, 101, 97, 100, 121]))
def table20 : Table 20 := .push table19 (Row.node (Kind.map 4) (fun (slot : Fin 4 × Bool) => if slot.2 then (List.get ([⟨12, by decide⟩, ⟨13, by decide⟩, ⟨5, by decide⟩, ⟨4, by decide⟩] : List (Fin 19))) slot.1 else (List.get ([⟨2, by decide⟩, ⟨7, by decide⟩, ⟨14, by decide⟩, ⟨16, by decide⟩] : List (Fin 19))) slot.1))
def table21 : Table 21 := .push table20 (Row.node (Kind.list 2) (List.get ([⟨7, by decide⟩, ⟨15, by decide⟩] : List (Fin 20))))
def table22 : Table 22 := .push table21 (Row.node (Kind.set 2) (List.get ([⟨0, by decide⟩, ⟨1, by decide⟩] : List (Fin 21))))
def table23 : Table 23 := .push table22 (Row.node (Kind.tuple 2) (List.get ([⟨17, by decide⟩, ⟨7, by decide⟩] : List (Fin 22))))
def table24 : Table 24 := .push table23 (Row.node (Kind.vector 16) (List.get ([⟨15, by decide⟩, ⟨9, by decide⟩, ⟨3, by decide⟩, ⟨10, by decide⟩, ⟨6, by decide⟩, ⟨7, by decide⟩, ⟨16, by decide⟩, ⟨14, by decide⟩, ⟨2, by decide⟩, ⟨11, by decide⟩, ⟨18, by decide⟩, ⟨8, by decide⟩, ⟨20, by decide⟩, ⟨21, by decide⟩, ⟨22, by decide⟩, ⟨19, by decide⟩] : List (Fin 23))))
end GraphInstance
