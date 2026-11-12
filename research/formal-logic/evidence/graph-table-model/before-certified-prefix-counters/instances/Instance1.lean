import GraphTable
set_option autoImplicit false
set_option maxRecDepth 100000
set_option maxHeartbeats 8000000
open FormalGraphTable
namespace GraphInstance
def table0 : Table 0 := .empty
def table1 : Table 1 := .push table0 (Row.scalar (Scalar.keyword [103, 114, 97, 112, 104, 46, 109, 111, 100, 101, 108, 46, 117, 110, 102, 97, 109, 105, 108, 105, 97, 114, 46, 52, 53]))
def table2 : Table 2 := .push table1 (Row.node (Kind.vector 2) (List.get ([⟨0, by decide⟩, ⟨0, by decide⟩] : List (Fin 1))))
def table3 : Table 3 := .push table2 (Row.node (Kind.vector 2) (List.get ([⟨1, by decide⟩, ⟨1, by decide⟩] : List (Fin 2))))
def table4 : Table 4 := .push table3 (Row.node (Kind.vector 2) (List.get ([⟨2, by decide⟩, ⟨2, by decide⟩] : List (Fin 3))))
def table5 : Table 5 := .push table4 (Row.node (Kind.vector 2) (List.get ([⟨3, by decide⟩, ⟨3, by decide⟩] : List (Fin 4))))
def table6 : Table 6 := .push table5 (Row.node (Kind.vector 2) (List.get ([⟨4, by decide⟩, ⟨4, by decide⟩] : List (Fin 5))))
def table7 : Table 7 := .push table6 (Row.node (Kind.vector 2) (List.get ([⟨5, by decide⟩, ⟨5, by decide⟩] : List (Fin 6))))
def table8 : Table 8 := .push table7 (Row.node (Kind.vector 2) (List.get ([⟨6, by decide⟩, ⟨6, by decide⟩] : List (Fin 7))))
def table9 : Table 9 := .push table8 (Row.node (Kind.vector 2) (List.get ([⟨7, by decide⟩, ⟨7, by decide⟩] : List (Fin 8))))
def table10 : Table 10 := .push table9 (Row.node (Kind.vector 2) (List.get ([⟨8, by decide⟩, ⟨8, by decide⟩] : List (Fin 9))))
def table11 : Table 11 := .push table10 (Row.node (Kind.vector 2) (List.get ([⟨9, by decide⟩, ⟨9, by decide⟩] : List (Fin 10))))
def table12 : Table 12 := .push table11 (Row.node (Kind.vector 2) (List.get ([⟨10, by decide⟩, ⟨10, by decide⟩] : List (Fin 11))))
def table13 : Table 13 := .push table12 (Row.node (Kind.vector 2) (List.get ([⟨11, by decide⟩, ⟨11, by decide⟩] : List (Fin 12))))
def table14 : Table 14 := .push table13 (Row.node (Kind.vector 2) (List.get ([⟨12, by decide⟩, ⟨12, by decide⟩] : List (Fin 13))))
def table15 : Table 15 := .push table14 (Row.node (Kind.vector 2) (List.get ([⟨13, by decide⟩, ⟨13, by decide⟩] : List (Fin 14))))
def table16 : Table 16 := .push table15 (Row.node (Kind.vector 2) (List.get ([⟨14, by decide⟩, ⟨14, by decide⟩] : List (Fin 15))))
def table17 : Table 17 := .push table16 (Row.node (Kind.vector 2) (List.get ([⟨15, by decide⟩, ⟨15, by decide⟩] : List (Fin 16))))
theorem original_expanded_nodes : (interpret table17 ⟨16, by decide⟩).expandedNodes = 131071 := by
  exact (expanded_node_count_agrees table17 ⟨16, by decide⟩).trans (by decide +kernel)
theorem original_depth : (interpret table17 ⟨16, by decide⟩).height = 16 := by
  exact (height_agrees table17 ⟨16, by decide⟩).trans (by decide +kernel)
#print axioms original_expanded_nodes
#print axioms original_depth
end GraphInstance
