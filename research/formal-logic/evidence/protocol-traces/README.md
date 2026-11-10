# Bounded protocol witness qualification

`qualification.json` binds exact code, SDK, native-worker and library identities
to the retained checks and examples.

- `checks.txt`: 473 passing assertions in four files, including 103 bounded trace
  assertions plus protocol, common-facade and API regression checks.
- `prefix-checks.txt`: 108 passing trace assertions, adding five checks that a
  repaired final state cannot erase an earlier invariant violation. The other
  103 overlap the combined run; do not add both totals as unique assertions.
- `initial-checks.txt`: the earlier passing 466-assertion snapshot, before the
  comparison reporting distinction and its regression checks were added.
- `examples.json`: nine subjects, eighteen native runs and ten independently
  replayed native counterexamples. Four safe answers have checked portable
  proofs; two remain solver-only within the retained search budget; two initial
  domains are vacuous. Search used 128 nodes and 128 arithmetic rows per attempt.
- `model-check.txt`, `Core.olean` and `model-qualification.json`: the current
  30-theorem Lean model. Five new finite-run laws check stuttering, retained state,
  persistent failure and the relationship to reachability. Their axiom audits
  are empty; two earlier integer ranking rules retain their stated assumptions.
- `doc-run.txt` and `doc-check.txt`: eleven executed dossier cells with an
  unchanged recheck.
- `browser-audit`: 288 passing live presentation/interaction checks and 28
  screenshots at phone and desktop widths, including the updated evidence view.

Native counterexamples retain original model availability and certificate
status. Scalar completion and execution-derived state observations are labelled
separately and accepted only after full term, state and observation replay.
Reporting fixtures and the authored transient-violation fixture in the test
file do not claim actual backend observations; the nine example subjects use
the real native backends.

These results concern bounded authored state models. Source handlers, live
actors, mailbox/scheduler effects, liveness and implementation/model soundness
remain outside this qualification. Compiler admission stays disabled.
