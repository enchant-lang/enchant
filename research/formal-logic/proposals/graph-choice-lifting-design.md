# Integer choices as a checked conservative extension

This is the next design after the qualified linear graph kernel. It is not an
implemented capability and is not part of the current SDK or dossier checkpoint.

Instead of distributing every integer conditional through arithmetic, introduce
one fresh mathematical Int variable for each original integer `ite` node. For
`v = if c then a else b`, derive these defining assertions:

```text
c  implies v = a
not c implies v = b
```

Replace that operational term occurrence with `v`. Addition, constant scaling
and comparisons can then remain in the linear Boolean/integer fragment. Every
original valuation has a unique extension to the fresh variables, so a checked
refutation of the derived counterexample excludes an original counterexample.
The extension relation itself needs a reviewed implementation and a separate
mechanical theorem; the current kernel theorem does not provide it automatically.

The boundary should have three pieces:

1. A graph transformation freshly admits the complete original subject, derives
   the target and a ledger of definitions, and reports both exact references.
   Its output is candidate data, never an original theorem.
2. The existing graph integer kernel freshly checks a proof about that exact
   derived target. It accepts no supplied normalized rows or cached inventory.
3. A closed original-subject wrapper reconstructs the transformation, checks
   target/certificate binding, and exposes the checked kernel result and the
   conservative-extension connection as separate evidence. No supplied status
   or callable can choose the transformation or establish that connection.

Use a deterministic fresh-name namespace derived from the complete original
subject reference and typed node ID, then explicitly refuse any collision with
an original variable. Do not rely on a hash prefix alone for hygiene. Bound the
original and generated variable counts before creating definitions. Integer and
Boolean variables share the collision check even though they have distinct sorts.

Preserve all original assumption rows and their source-node ledger. Generated
definitions belong to a separate ledger; they are not user preconditions and
must not make an impossible original context appear feasible. Their provenance
can name a freshly reconstructed typed-node ID when the SDK does not expose an
original internal source-node mapping; do not label that ID as an original graph
node. Original assertion roots do have exact source references.

Rewrite only operational fields: assertion terms, claim/counterexample and
observable payload/definedness/within terms. Preserve labels, origins, scope,
profiles, observation keys and unrelated metadata as graph fragments. A global
node replacement is insufficient: canonical graph sharing can make an active
term and an unrelated provenance field point at the same node. Rewriting that
node everywhere would change provenance. Use the same descriptor traversal as
the installed observation reader, with separate memoization for term and value
contexts. A formal value's ignored metadata remains untouched.

Preserve observations rather than dropping them to make the target easier to
check. Derive the counterexample from the rewritten claim while preserving its
original outer metadata. Append generated assumption descriptors consistently
with generated assertion rows. All other original fields remain byte-bound to
the connection's original subject.

Reserve fresh admission, graph reconstruction/import work, generated nodes and
kernel checking before their respective operations. Shared graph assembly must
not materialize argument trees or unfamiliar metadata. Cap choices, variables,
atoms, coefficient growth and proof contexts independently of a larger work
allowance. Start with Bool/Int affine syntax plus integer `ite`; ground division
and modulus need a separate exact Euclidean rule and their own resource checks.

The first checks should cover nested choices, a false conditional property,
fresh-name collision, original and generated assumption ledgers, shared active
terms also occurring in untouched provenance, formal-value observations, low
budgets, unsupported syntax and zero native/oracle execution. Compare actual
legacy piecewise certificates through an explicit untrusted translator; the
fresh target checker must reject any mistaken translation. Original-subject
packet reopening, Source/contract use and runtime integration follow only after
those checks pass.
