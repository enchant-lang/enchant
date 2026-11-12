# Typed response relations and measured fault sets

Implementation draft under qualification. The selected research SDK still points
to checkpoint 36 until this batch has passed its immutable-SDK checks.

A response contract contains named typed fields and every law. `formal.response`
is the portable relation and question constructor. `formal.response-runtime`
connects reviewed source ANF, concrete execution and native answers. Veritas mock
and fault APIs consume these pieces instead of constructing SMT scripts.

```beam-lisp
(def weather
 (mock/contract-from [[:temp (veritas/int-of -40 60)] [:code (veritas/int-of 200 299)]]
                    ['(<= temp 60) '(>= code 200)]))
(mock/synth {:backend :z3} weather)
(mock/synth {:backend :oxiz} weather)
(mock/prepare weather {:pins {:code 220}})
```

`contract-from` compiles every quoted law. Unsupported source rejects the whole
construction. There is no weaker successful contract. Generator fields retain
runtime admission; products, enums and length abstractions keep their profiles.
The mathematical `mock/contract` constructor instead takes native sorts and a
one-shot builder over field terms. It supports the term vocabulary without
claiming a BL source translation. Mathematical Reals, BV and FP values retain
their explicit BL data encodings; Reals never silently become runtime floats.

Quoted source expressions, function properties, coverage guards and response
laws can now enter the compiler as bounded code data. The existing compiler's
first-order datum conversion rebuilds Reader nodes. String source remains an
explicit Reader path. Runtime inputs use literal ANF arguments. Pretty printing
is for source descriptions, not for passing data to a backend or executing a
quoted predicate. General runtime-only sampling still has the separate callable
ownership work described in CALLABLE-CUSTODY.md.

A semantic assumption carries constraints, model admission and scope in addition
to its Boolean payload. The common question builder now retains all of them,
including labelled semantic assumptions. Retained context assumptions also keep
their admission scope and profiles in the full question returned with an answer. The preceding SDK's baseline gives
both engines a weaker question and demonstrates five failures. Those old
questions retain their original meaning; newly constructed questions include
the missing conditions. No proof format or term interpretation is redefined.

| Operation | Question and result |
| --- | --- |
| synth | A complete SAT question. A value becomes witnessed only after independent term validation, domain admission and the appropriate forward check. |
| synth-invalid | At least one law fails, including an admitted source predicate raising during invocation. |
| isolate | Prove one law under the others. A replayed counterexample supplies an isolated fault; native UNSAT is an unchecked implication claim. Infeasible other laws are vacuous. |
| total-error | Every law fails. This can be impossible even when ordinary invalid responses exist. |
| check-result | Independent mathematical evaluation or exact source ANF execution on a complete response. Unknown, domain failures and execution errors remain separate from violations. |
| synth-boundary | Exponential bracketing and binary refinement over the full integer domain, followed by a strict no-better-response question. A budget or unknown answer never establishes an optimum or unboundedness. |

Boundary results keep feasible-response evidence separate from the final
unchecked optimality claim. The top-level claim question is the final UNSAT
question, and its feasible value is not mislabelled as that question's witness.
The ledger retains both parts as recorded evidence without granting authority.

Constructors accept an optional third argument, `{:namespace :response/a}`.
Generated field identities include the complete field name, sort and namespace.
Use separate explicit namespaces for independent response coordinates in one
retained context; a repeated declaration in the same namespace names the same
logical coordinate. Explicit semantic models keep their own variable identities.

A mock server retains its first replayed answer per exact key. This is stability
within one server instance, not canonical model selection across backends or
independent servers. Admission stops at capacity without evicting old answers.
A server borrowing a context refuses use after that context changes or expires.

Fault databases measure supplied concrete responses. Only known violated laws
produce edges; unresolved checks do not become violations or redundant mutant
signatures. Complete empty signatures remain visible. Reports close their
internal database and return data; callers needing an owned database use
`build-db` and close its connection explicitly. These coverage reports describe
the supplied concrete suite, not every possible fault in an unbounded domain.

Runtime Unicode text outside the solver String alphabet remains a model limit,
not an invented law violation. Native unsupported, unknown and incomplete model
answers remain visible. No result here establishes checker soundness, source
preservation, whole-language totality or compiler proof authority.
