# Core Int/Bool with explicit outcomes, version 1

The executable definition is `formal.core`, profile
`:bl/core-int-bool-outcomes-v1`. This is a specified fragment for the formal
foundation, not a claim to specify all current BL or OTP behavior.

```
T ::= Int | Bool
e ::= integer | boolean | x | let x = e in e | if e then e else e
    | do e ... e | op(e, ...) | raise error-name : T
```

Integers are mathematical unbounded integers. Bool is a distinct type.
Conditionals require Bool; equality requires operands of the same type. Binding
is lexical and may shadow an outer name. A block is nonempty and has the type
of its last expression. Both conditional branches have the same type. Error
names are keywords; a raised expression declares its result type.

Operations are integer add/subtract/multiply/negate, typed equality, integer
comparisons, Boolean not/and/or, and integer quot/rem/mod. All operation operands
are evaluated eagerly, from left to right. Conditional branches are selective.

An evaluation produces either `returned(value, T)` or `raised(error-name, T)`.
The first raised operand, initializer or block expression ends that evaluation;
later expressions are not evaluated. A condition that raises also raises the
conditional. An untaken branch contributes no runtime result or failure.

`quot` truncates toward zero. `rem(a,b) = a - b * quot(a,b)`. `mod` adjusts
nonzero remainder by the divisor when their signs differ, giving the divisor's
sign. A zero divisor raises `:zero-divisor` for all three operations. User-raised
error names remain distinct. No hardware width, Decimal, floating conversion,
host exception payload or scheduler behavior is inferred by this profile.

There is no recursion, looping, function call, implicit cast, eval, mutable state
or foreign operation in this grammar. Evaluation follows a finite syntax tree;
each visited subtree is smaller. Primitive integer operations are assumed to
terminate mathematically. This is a structural termination argument, not a
machine-checked proof about the BL implementation. The type checker reports its
metatheory status explicitly. Its syntactic `:raise` effect is conservative,
including errors in unreachable branches.

The reference interpreter returns `:invalid-input` for values that do not match
the declared inputs. A configured evaluation step limit produces `:incomplete`,
never a modeled error. Implementation or host resource failure is outside the
core's mathematical exception semantics.

## Three independent paths

- `formal.core/typecheck` validates canonical data, lexical scope and types.
  `formal.core/evaluate` is the concrete reference semantics.
- `formal.core-symbolic/lower` constructs separate terms for successful return,
  returned value and exact error identity. Its common outcome relation checks
  return/raise, value when returning, and error name when raising. A shared
  injective error code table keeps names distinct across two programs.
- `formal.elaborate/prepare` consumes the real compiler's resolved ANF for one
  reviewed BL expression. It admits only the declared Int/Bool inputs and known
  intrinsics. It converts an Int used as a condition to “evaluate it, then true,”
  preserving BL truthiness and possible failure. Nil, dynamic collections,
  unreviewed calls and effects are refused rather than approximated.

Elaboration and symbolic interpretation are reviewed implementations. Their
testing does not constitute a proof of compiler correctness or a mechanically
proved connection from arbitrary BL source to this core. Macros and compiler
front-end execution remain a separate build-time boundary. Certificates for the
resulting terms retain `:source-connection :not-established`.

Core equivalence questions can use either native backend. The first independent
certificate checker can handle the Boolean/linear Int subset of those questions;
division, nonlinear operations and nonconstant Int-valued branches may still
require unsupported proof rules. Solver support and independent proof support
are reported separately.

The separate [Lean model](metatheory/README.md) now mechanically checks typed
model outcomes, selected evaluation laws and ranking rules. Its proof receipt
keeps the BL implementation/ANF/term/compiler correspondences explicitly
unproved. Bound names in the BL core are canonicalized to avoid free-name
capture and compiler fresh-counter changes in semantic identities.
