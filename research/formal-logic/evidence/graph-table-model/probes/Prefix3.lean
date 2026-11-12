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
end GraphInstance
