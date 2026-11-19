import Base

def serial(+n: U32, x: U32) -> U32:
  serial.go(n, x, U32.is_zero(n))

def serial.go(n: U32, +x: U32, done: Bool) -> U32:
  match done:
    case True{}: x
    case False{}:
      +t = (x * 3 + 1 : U32)
      serial((n - 1 : U32), wrap(t))

def wrap(+t: U32) -> U32:
  wrap.go(t, U32.is_lt(t, 65521), U32.is_lt(t, 131042))

def wrap.go(t: U32, small: Bool, medium: Bool) -> U32:
  match small medium:
    case True{} _: t
    case False{} True{}: (t - 65521 : U32)
    case False{} False{}: (t - 131042 : U32)

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

def finish(f: File, result: U32) -> IO(Unit):
  do IO<Unit>:
    u : Unit <- IO.print(U32.show(result))
    serve(f)

def bytes(+k: U32, p: File & Result<&1, &1, U32 & String, List<&2, U32>>) -> IO(Unit):
  (f, res) = p
  do IO<Unit>:
    xs : List<&2, U32> <- IO.pass(List<&2, U32>, res)
    finish(f, consume(xs, U32.is_eq(k, 3), U32.is_eq(k, 4)))

def consume(xs: List<&2, U32>, scan_it: Bool, map_it: Bool) -> U32:
  match scan_it map_it:
    case True{} _: scan(xs, False{}, 0)
    case False{} True{}: sum(graded(xs), 0)
    case False{} False{}: fused(xs, 0)

def dispatch(f: File, k: Nat, n: U32, seed: U32) -> IO(Unit):
  match k:
    case 0n: finish(f, seed)
    case 1n+0n: finish(f, serial(n, seed))
    case 1n+1n+0n: finish(f, tree!(U32.to_nat(n), seed))
    case 1n+1n+1n+rest:
      do IO<Unit>:
        p : File & Result<&1, &1, U32 & String, List<&2, U32>> <- File.read_bytes(f, n)
        bytes((U32.from_nat(rest) + 3 : U32), p)

def header(f: File, h: List<&2, U32>) -> IO(Unit):
  match h:
    case k <> hi <> lo <> seed <> Nil{}: dispatch(f, U32.to_nat(k), (hi * 256 + lo : U32), seed)
    case Nil{}: File.close(f)
    case _: IO.die(Unit, 2, "incomplete request")

def serve(f: File) -> IO(Unit):
  do IO<Unit>:
    p : File & Result<&1, &1, U32 & String, List<&2, U32>> <- File.read_bytes(f, 4)
    (src, res) = p
    h : List<&2, U32> <- IO.pass(List<&2, U32>, res)
    header(src, h)

def main() -> IO(Unit):
  do IO<Unit>:
    f : File <- IO.try(File, File.open("/dev/stdin", "r"))
    serve(f)
