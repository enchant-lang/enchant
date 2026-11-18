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

# Stream bounded file chunks through one process. Each chunk has 32 leaves.
def wrote(pair: File & Result<&1, &1, U32 & String, Unit>) -> IO(File):
  (f, result) = pair
  do IO<File>:
    u : Unit <- IO.pass(Unit, result)
    return f

def frame(out: File, pair: File & Result<&1, &1, U32 & String, List<&2, U32>>) -> IO(File & File):
  (f, result) = pair
  do IO<File & File>:
    +xs : List<&2, U32> <- IO.pass(List<&2, U32>, result)
    rows : Rows = split(5n, List.length(&2, U32, xs), xs)
    output : List<&2, U32> = render!(rows)
    w : File & Result<&1, &1, U32 & String, Unit> <- File.write_bytes(out, output)
    dest : File <- wrote(w)
    return (f, dest)

def stream(n: Nat, files: File & File) -> IO(Unit):
  (src, dst) = files
  match n:
    case 0n:
      do IO<Unit>:
        u : Unit <- File.close(src)
        File.close(dst)
    case 1n+p:
      do IO<Unit>:
        read : File & Result<&1, &1, U32 & String, List<&2, U32>> <- File.read_bytes(src, 256)
        next : File & File <- frame(dst, read)
        stream(p, next)

def sized(out: File, pair: File & Result<&1, &1, U32 & String, U32>) -> IO(Unit):
  (src, result) = pair
  do IO<Unit>:
    n : U32 <- IO.pass(U32, result)
    stream(U32.to_nat(U32.div(U32.add(n, 255), 256)), (src, out))

def main() -> IO(Unit):
  do IO<Unit>:
    f : File <- IO.try(File, File.open("input.rgb", "r"))
    out : File <- IO.try(File, File.open("bend.rgb", "w"))
    size : File & Result<&1, &1, U32 & String, U32> <- File.size(f)
    sized(out, size)
