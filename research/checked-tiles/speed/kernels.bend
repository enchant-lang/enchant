import Base

def wrap.go(t: U32, small: Bool, medium: Bool) -> U32:
  match small medium:
    case True{} _: t
    case False{} True{}: (t - 65521 : U32)
    case False{} False{}: (t - 131042 : U32)

def serial(n: Nat, x: U32) -> U32:
  match n:
    case 0n: x
    case 1n+p:
      +t = (x * 3 + 1 : U32)
      serial(p, wrap.go(t, U32.is_lt(t, 65521), U32.is_lt(t, 131042)))

def tree(d: Nat, +x: U32) -> U32:
  match d:
    case 0n: (x * x + 1 : U32)
    case 1n++p:
      l r = tree(p, x) tree(p, (x + 1 : U32))
      (l + r : U32)

def scan(xs: List<&2, U32>, inside: Bool, runs: U32) -> U32:
  match xs:
    case Nil{}: runs
    case +c <> tail:
      +digit = Bool.and(U32.is_lt(47, c), U32.is_lt(c, 58))
      scan(tail, digit, (runs + Bool.to_u32(Bool.and(digit, Bool.not(inside))) : U32))

def grade(x: U32) -> U32:
  U32.div((x + 255 : U32), 2)

def graded(xs: List<&2, U32>) -> List<&2, U32>:
  match xs:
    case Nil{}: Nil{}
    case x <> tail: grade(x) <> graded(tail)

def sum(xs: List<&2, U32>, total: U32) -> U32:
  match xs:
    case Nil{}: total
    case x <> tail: sum(tail, (x + total : U32))

def fused(xs: List<&2, U32>, total: U32) -> U32:
  match xs:
    case Nil{}: total
    case x <> tail: fused(tail, (grade(x) + total : U32))

def consume(xs: List<&2, U32>, scan_it: Bool, map_it: Bool) -> U32:
  match scan_it map_it:
    case True{} _: scan(xs, False{}, 0)
    case False{} True{}: sum(graded(xs), 0)
    case False{} False{}: fused(xs, 0)

def finish(f: File, result: U32) -> IO(File):
  do IO<File>:
    u : Unit <- IO.print(U32.show(result))
    return f

def bytes(+k: U32, p: File & Result<&1, &1, U32 & String, List<&2, U32>>) -> IO(File):
  (f, res) = p
  do IO<File>:
    xs : List<&2, U32> <- IO.pass(List<&2, U32>, res)
    finish(f, consume(xs, U32.is_eq(k, 3), U32.is_eq(k, 4)))

def dispatch(f: File, k: Nat, n: U32, seed: U32) -> IO(File):
  match k:
    case 0n: finish(f, seed)
    case 1n+0n: finish(f, serial(U32.to_nat(n), seed))
    case 1n+1n+0n: finish(f, tree!(U32.to_nat(n), seed))
    case 1n+1n+1n+rest:
      do IO<File>:
        p : File & Result<&1, &1, U32 & String, List<&2, U32>> <- File.read_bytes(f, n)
        bytes((U32.from_nat(rest) + 3 : U32), p)

law serve:
  for fuel : Nat
  for f : File
  IO(Unit)

def header(fuel: Nat, f: File, h: List<&2, U32>) -> IO(Unit):
  match h:
    case k <> hi <> lo <> seed <> Nil{}:
      do IO<Unit>:
        next : File <- dispatch(f, U32.to_nat(k), (hi * 256 + lo : U32), seed)
        serve(fuel, next)
    case Nil{}: File.close(f)
    case _: IO.die(Unit, 2, "incomplete request")

def received(fuel: Nat, p: File & Result<&1, &1, U32 & String, List<&2, U32>>) -> IO(Unit):
  (src, res) = p
  do IO<Unit>:
    h : List<&2, U32> <- IO.pass(List<&2, U32>, res)
    header(fuel, src, h)

def serve(fuel, f):
  match fuel:
    case 0n: File.close(f)
    case 1n+p:
      do IO<Unit>:
        h : File & Result<&1, &1, U32 & String, List<&2, U32>> <- File.read_bytes(f, 4)
        received(p, h)

def main() -> IO(Unit):
  do IO<Unit>:
    f : File <- IO.try(File, File.open("/dev/stdin", "r"))
    serve(65536n, f)
