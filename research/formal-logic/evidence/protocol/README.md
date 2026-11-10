# State/protocol qualification

`qualification.json` records exact source hashes, the tested commit, immutable
SDK pin, native worker and library identities.

- `checks.txt`: 648 passing assertions in five files, including 133 new protocol
  assertions. This covers proof coverage/tampering, both native engines, concrete
  conservation traces, simultaneous replacement, guard/update failure, input
  assumptions, vacuity, nonlinear uncertified evidence and identity encoding.
- `features.json` and `advanced.json`: 92 rechecked original questions. Their
  backend verdicts match the retained historical receipts. This does not claim
  that all 187 original questions were rerun at this checkpoint.
- `examples.json`: six closed state-model definitions and twelve native runs,
  with portable proof objects where available. Their concrete traces are
  separately authored examples, not decoded induction countermodels. Five
  admissible traces replay; the empty-domain initial state is rejected.
- `model-check.txt`, `Core.olean` and `model-qualification.json`: 25 checked Lean
  model theorems and their printed axiom dependencies. The three new state
  induction/failure-exclusion audits are empty. The two integer ranking proofs
  retain the standard assumptions recorded in the receipt.
- `doc-run.txt` and `doc-check.txt`: ten executed dossier cells, then an unchanged
  recheck of their results.

The protocol proof concerns every finite prefix of the declared model, with
explicit input assumptions. An induction countermodel may be unreachable.
Concrete traces and a native solver's induction witnesses remain separate.
No live actor, liveness, source/compiler correspondence or mechanically verified
BL checker claim follows from this qualification.
