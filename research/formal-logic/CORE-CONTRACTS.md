# Checked contracts on Core outcomes

A program contract describes admission, the condition a returned value must satisfy and the named errors that may escape. Its exact typed question is data that either native backend can inspect. The composition checker connects an independently checked entailment of that question to evaluation of the contained Core program.

Given an input environment for which the exact precondition evaluates to true, the theorem gives the following facts about the Core outcome.

- If the program returns, the symbolic payload is defined and equals the returned value. The compiled postcondition term evaluates to true.
- If the program raises, the contract permits a raised outcome and the error belongs to its permitted names. The checker derives name membership through the checked numeric catalogue.
- If the policy requires a return, the raised case is contradictory. A finite Core evaluation therefore gives a value satisfying the postcondition for every admitted input.

The `ensures` builder runs at preparation time on symbolic inputs and payload. Its resulting term appears in the theorem. This stage uses the existing partial mathematical integer and Boolean semantics with scalar and named-record Core outcomes. The entailment still needs an accepted certificate in the existing refutation fragment. Unsupported or too expensive questions can leave the composed result open.

## Beam Lisp interface

```clojure
(def contract-proof (formal/verify-contract definition))
(def certificate (get-in contract-proof [:proof :certificate]))
(def prepared (formal/core-contract-data definition certificate))
(def checked-data
  (formal/check-core-contract-data definition certificate (:packet prepared)))
```

`core-contract-feasibility` exposes the SAT question over the same assumptions. To request an admission proof, supply `{:witness {:bindings bindings}}` as the third export argument, or supply `{:witness {:packet packet}}` from `term-witness-from-result`. Use the original assertion input names and concrete values. The witness covers exactly the assertion variables. The checker completes unused slots with zero or false and proves that the resulting input satisfies the precondition. Both Z3 and OxiZ can supply candidates through this interface.

An omitted witness leaves a conditional theorem. A false precondition can admit no input and still have a conditional proof. The checker reports admission separately.

## Independent check

Export the packet as JSON with `interop/->json`. Run the capped checker with the pinned Lean model.

```sh
research/formal-logic/check-core-contract \
  research/formal-logic/evidence/core-contracts/examples/unused-slots.json \
  --output /tmp/enchant-contract-example --axiom-policy choice-free
```

The checker validates and recomputes the canonical identities. It checks both premise modules anew and imports their compiled objects from that invocation. The Core proof uses every declared input. The entailment may omit some of them, so the checker maps slots by exact input name and sort. Lean proves equality of the remapped original question and the question constructed from the exact Core outcome and policy. This includes both assertions and the entire claim. The optional witness then gives a separate existential theorem by applying the universal result.

The runner audits the axioms of the composed theorem. Signed quotient correspondence in the division example uses `Classical.choice` under the standard policy. The other seven examples pass the choice-free policy. See [the execution reports](evidence/core-contracts/execution/accepted.json) and [the rejected proof substitutions](evidence/core-contracts/execution/rejected.json).

The data connection to the original BL subject requires `check-core-contract-data` against that subject and certificate. Source contracts can run phase code during fresh preparation. The named-data codecs and Source-to-Core connection are reviewed. The theorem covers the contained Core program, while compiler and BEAM preservation remain open. It grants no compiler authority. Termination of ordinary loops and actor behavior require their own model composition.
