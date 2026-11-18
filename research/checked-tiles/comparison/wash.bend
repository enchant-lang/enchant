import Base

type Rows is Type:
  Leaf{xs: List<&2, U32>}
  Pair{a: Rows, b: Rows}

def split(d: Nat, +n: Nat, +xs: List<&2, U32>) -> Rows:
  match d:
    case 0n: Leaf{xs}
    case 1n++p:
      +half = Nat.div(n, 2n)
      left = List.take(&2, U32, xs, half)
      right = List.drop(&2, U32, xs, half)
      Pair{split(p, half, left), split(p, Nat.sub(n, half), right)}

def wash(xs: List<&2, U32>) -> List<&2, U32>:
  match xs:
    case Nil{}: Nil{}
    case x <> t: U32.div(U32.add(x, 255), 2) <> wash(t)

def render(rows: Rows) -> List<&2, U32>:
  match rows:
    case Leaf{xs}: wash(xs)
    case Pair{l, r}:
      a b = render(l) render(r)
      List.append(&2, U32, a, b)

def finish(pair: File & Result<&1, &1, U32 & String, Unit>) -> IO(Unit):
  (f, result) = pair
  do IO<Unit>:
    u : Unit <- IO.pass(Unit, result)
    File.close(f)

def frame(pair: File & Result<&1, &1, U32 & String, List<&2, U32>>) -> IO(Unit):
  (f, result) = pair
  do IO<Unit>:
    +xs : List<&2, U32> <- IO.pass(List<&2, U32>, result)
    u : Unit <- File.close(f)
    rows = split(5n, List.length(&2, U32, xs), xs)
    output = render!(rows)
    out : File <- IO.try(File, File.open("bend.rgb", "w"))
    written : File & Result<&1, &1, U32 & String, Unit> <- File.write_bytes(out, output)
    finish(written)

def main() -> IO(Unit):
  do IO<Unit>:
    f : File <- IO.try(File, File.open("input.rgb", "r"))
    pair : File & Result<&1, &1, U32 & String, List<&2, U32>> <- File.read_bytes(f, 3145728)
    frame(pair)
