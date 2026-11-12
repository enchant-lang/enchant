# Properties that follow a function into the solver

`veritas.property/prepare` turns one plain Beam Lisp `defn`, a quoted Boolean
property and a generator domain into an inspectable `formal.query` value.
`prove` runs that question through the standard oracle effect on either backend.

```beam-lisp
(require '[veritas.property :as property] '[veritas :as v])
(def floor '(defn floor [c] (if (< c 0) 0 c)))
(def question (property/prepare floor '(>= result 0) (v/int-of -1000000 1000000)))
(property/prove {:backend :z3} floor '(>= result 0) (v/int-of -1000000 1000000))
(property/prove {:backend :oxiz} floor '(> result 0) (v/int-of -1000000 1000000))
```

The interface takes an options map. Native UNSAT yields `:solver-claim` with
`:answer :certificate :status` equal to `:not-checked`. Checking a portable
certificate for the question is separate from proving the compiler and runtime
connection. The result retains its complete question, canonical identity,
assumptions, model scope, reviewed source connection and native answer.

A law requires the target to return, the property to return, and the property's
value to be exactly `true`. A crash in the target fails the law even when the
property ignores `result`. A crash in the property is a distinct failed outcome.
Empty input domains yield `:vacuous`; timeout and unknown remain unresolved.

A source refutation requires two observations: independent term-model replay,
and execution of the exact compiler ANF used for translation. Runtime arguments
travel as actual values into ANF literals. The replay checks the target's
returned value or raisedness, then the property's returned value or raisedness.
Compilation or publication failures are execution errors, distinct from a
target raise. The exact emitted module is leased through invocation and retired
before replay completes. A disagreement or unavailable input yields `:candidate` with the underlying
answer retained. A reproduced failure yields `:refuted`, `:witness`, `:result`,
`:crash` and a detailed `:runtime-replay` record.

The target has one unguarded clause with up to 16 distinct variable parameters.
`result` is reserved for its output. A `tuple-of` supplies exactly one generator
per argument, including zero or one arguments; a scalar generator supplies one
argument. Arity mismatches, destructuring, multiple source forms, recursion,
foreign calls and unresolved globals are refused.

`veritas/GenTerms` gives generators a term-valued `gen-term` method alongside
sampling and enumeration. Bounded integers, Booleans and homogeneous finite
sets of integers, Booleans or strings have reviewed domains. An empty finite set
is a false domain. The [composed Veritas models](VERITAS-TERMS.md) add enums,
positional products, explicit collection-length abstractions and text prefixes.
Concrete replay checks those models' runtime domains and output profiles.
Element reasoning, runtime floats and grapheme bounds retain their own limits.
Legacy SMT encodings grant no meaning to this source interface.

The SDK's `formal.source` uses resolved compiler ANF and the exact reviewed
intrinsic catalogue. It preserves integer truthiness, nil, lazy branches,
toward-zero quotient and remainder, divisor-sign modulus, and zero-divisor
raisedness. Return sorts are inferred. The source environment is explicitly
`formal.source.intrinsics`; this does not establish equivalence to an arbitrary
ambient namespace with rebound functions. Macro expansion can execute
compiler-phase code. The ANF-to-term relation and the compiler/runtime connection
remain reviewed implementations; compiler proof authority is false.

Unsupported source returns `:unsupported` without running the target.
`{:fallback :sample :sample-n 64}` explicitly requests sampled execution for that
case. A successful sample yields `:witnessed`. An unknown solver answer never
falls through to sampling. `hypothesis` remains the direct sampling interface;
its printed data literals preserve quoting and escaping.

The qualified guarded-division example `(if (= n 0) 0 (quot 1 n))` at input zero
has a true, normally returning term interpretation. Z3 settles its property;
OxiZ 0.3.4 returns unknown on that exact question. Backend decision strength is
reported separately from the shared source meaning.

Quoted function and predicate forms now enter through the compiler's bounded
first-order datum conversion. Strings retain the explicit Reader path. Literal
quotes, backslashes, newlines and NUL survive the source/property/coverage checks
as data; pretty printing is only a display description. The related
[response interface](RESPONSE-CONTRACTS.md) compiles every law and executes each
exact ANF on the concrete response. Unsupported laws reject construction.
