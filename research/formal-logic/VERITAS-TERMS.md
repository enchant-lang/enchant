# One question across generator theories

`veritas/check`, `exists`, `for-all` and `covers` take options maps and use
complete `formal.query` values. `prepare` exposes the question before solving.
`{:backend :z3}` and `{:backend :oxiz}` select native engines;
`{:engine :terms}` requires a reviewed source/domain translation.

The default `:auto` engine tries terms, then actual finite enumeration or
sampling when source preparation declines. An unresolved native answer keeps
its question and diagnostics. It never falls through to sampling. Explicit
`:enumerate` and `:sample` select the runtime engines; `:seed` and `:n` control
sampling. A shared `with-solver` callback owns a typed question context.

| Result | Meaning |
| --- | --- |
| `:solver-claim` | Native UNSAT with an unchecked certificate; `:none true` marks an existential absence claim. |
| `:witnessed` | An existential runtime witness, or no sampled universal failure. Engine and completeness distinguish them. |
| `:refuted` | A concrete failing universal input. Native candidates require term replay and execution of the translated predicate ANF. |
| `:exhausted` | The declared finite domain was completely tested. |
| `:vacuous` | A universal query has no admitted inputs. |
| `:unknown` | No decision, including unsuccessful existential sampling. |
| `:candidate` | A native model cannot yet establish a runtime witness. |

False and nil are ordinary witnesses. Search uses a separate presence marker.
No sampled absence implies a redundant law. Full source/compiler correctness
remains a reviewed connection, separate from mathematical certificates.

Typed generator models cover bounded integers, Booleans, finite scalar sets,
complete keyword/payload enums, positional products, and vector-length
abstractions. Enum names retain namespaces. Payload constructors admit their
actual declared shapes, including false Boolean payloads. Products compose
these models, so an enum and a length abstraction can share one question.

The vector model erases elements explicitly. `count`, `empty?`, `conj`, `rest`
and `pop` preserve modeled lengths and raisedness. `rest` produces a list;
`pop` on an empty vector raises. Element lookup and collection equality require
element models and decline this abstraction. A SAT length is materialized as a
range vector only for concrete replay, with a 4,096-element materialization
limit. The logical domain keeps its declared bounds when replay is unavailable.

String domains keep runtime units precise. `string-of` bounds total BL grapheme
counts; its samples respect those bounds and use the runtime engine. `text-of`
models unbounded valid UTF-8 text with a prefix using solver string terms.
`String/starts_with?` has reviewed prefix semantics; counting
`String/codepoints` explicitly models code-point length. Direct BL `count` on
text does not borrow SMT string length. Solver text is an abstraction whose
candidate values must pass actual UTF-8/domain checks and predicate execution.
Runtime float intervals do not borrow the mathematical Real sort.

Coverage compiles a selection function from the original parameter and guard
nodes, replacing bodies with true and appending a false fallback. Original
bodies and their macros are neither compiled nor executed. Plain fixed-arity
parameters are supported; each clause keeps its own names. Guards accept only
true and decline on a raise. Literal false and nil guards remain present.
Unsupported patterns stay explicit. Runtime-only guard checks retain compilation
errors separately from uncovered inputs. These transformations are reviewed,
not a general compiler-preservation theorem.

Legacy SMT helpers remain for the separate mock/fault consumers. Their
migration and richer source summaries remain active work.

On the exact shared Unicode-prefix law, Z3 reports UNSAT and OxiZ 0.3.4
returns unknown. Constructing a native string term and deciding its query are
different capabilities; the native answer keeps that distinction.
