# Prepare the shared terms the engines already understand

The project prototype now prepares typed term roots directly from a checked
public data graph. Its argument traversal keeps node references. One batch
materializes operation, sort and explicit data components; local constructor
checks and binder-environment checks then produce the existing native table.
The module remains a project preview on SDK 44, rather than part of that SDK or
the managed `logic/run-graph` path.

The [qualification](evidence/term-forest/qualification.json) retains:

* 521 focused assertions, including exact existing-export comparisons across
  native primitive fixtures, forged inputs and binder-environment reuse.
* All 187 preceding questions with exactly the same native definitions and
  ordered root IDs as the selected SDK's exporter. Preparation uses zero
  managed query calls.
* 38 actual raw native scopes across 19 theory families, with the existing
  declared status expectations. Z3 reports 15 UNSAT, three SAT and one
  unsupported result; OxiZ reports eleven UNSAT, three SAT, two unknown and
  three unsupported results. These are native statuses, not independently
  checked proof or replay verdicts.
* Two more raw scopes for a graph-built Boolean sharing example. Its 45 stored
  data nodes describe 1,572,852 expanded data nodes and 131,071 term occurrences.
  The canonical graph is 1,349 bytes. Preparation produces 17 native definitions
  in 17 scope states; both engines receive a 772-byte request and return the
  observed true root.

Successful raw transport invalidates the owner's managed portable-context
accounting. The checks exercise that boundary. They do not pass a prepared map
off as a managed question or execution receipt. Every worker/library identity
comes from the same immutable SDK; the existing 500 ms solver and 2,000 ms hard
deadlines remain in force.

## What improves, and what still costs work

The useful capability is direct preparation from graph-built input, including
large sharing and unrelated unadmitted history. A reused bound term is checked
under each environment where it occurs. The full input graph reference retains
unrelated contents even when those contents are not materialized.

The first timing run is deliberately retained, including its limits. Across
187 cases, graph preparation totals 15,454 ms versus 4,700 ms for the existing
exporter; medians are 38 ms and 2 ms. Initial graph conversion is separate:
30,189 ms in total. Small cases therefore pay more checking/graph overhead.
The closure example is more favorable: 123 definitions prepare in 870 ms versus
2,055 ms for legacy export, after an 8,192 ms initial graph conversion.
These are serial preparation observations, not solver or end-to-end speed
benchmarks. The current managed path still rebuilds selected terms and the
independent reply checker still has its existing representation costs.

## The semantic boundaries stay visible

The prototype checks each local rule with the existing constructors using
privately derived child-sort descriptors. It separately checks free variables,
nominal binders and scope-state capacity. A caller cannot submit a prepared
output map as an already checked graph. The constructor's ordered list/vector
argument aliases remain accepted, while the exact saved graph still records
which original container was used.

Those compatibility checks are not a mechanical soundness theorem for the new
checker. The earlier structural/selection proofs do not establish typed-term
interpretation, runtime admission or compiler preservation. Native UNSAT remains
unchecked, and compiler authority stays false.

Next, prepare complete questions without rebuilding their term trees, including
claim/counterexample agreement and structured observations. Managed promotion
then needs validation inside the actual owner turn, retained-assumption and
revision checks, and owner-local ID allocation. The common query/effect/reply
interface should continue to take the original question. Review the remaining
primitive-data, naming and observation-container rules before that promotion;
see [the architecture plan](TERM-FOREST-PLAN.md).

Implementation: [graph preparer](src/formal/term-forest.bl),
[focused controls](test/term_forest_test.bl),
[187-question comparison](term-forest-check.bl),
[native family scopes](term-forest-native.bl), and
[sharing example](term-forest-sharing.bl).
