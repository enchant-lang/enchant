# A conditional theorem and a usable obligation need separate judgments

The scalar SDK remains frozen during qualification. This review records a
concrete next semantic change; it does not claim that change is implemented.

## What the code currently does

`formal.query/make` defaults `:vacuity` to `:report`, while `validate!` does not
close its vocabulary. `formal.graph-question` and `formal.question-graph` read
only the exact `:allow` keyword specially; everything else becomes `:report`.
Native graph execution preflights assumption consistency for every policy other
than `:allow`. Its UNSAT report is still a native claim, including a report about
inconsistent premises. The independent finite checker correctly establishes
conditional entailment and leaves feasibility `:not-established`.

There is no implemented distinct `:reject` policy. A spelling mistake or a
proposed `:reject` silently selects report behavior today. The common evidence
conclusion also does not separately say whether a caller's nonvacuity requirement
has been discharged. These are preview semantic issues to fix, rather than API
promises to document as existing features.

## Proposed closed vocabulary and judgments

Keep three independent facts: the checked conditional statement, the checked
feasibility of its complete background, and the consumer policy judgment.
Changing the last must never erase or strengthen either mathematical result.

| Policy | Witnessed feasible background | Checked inconsistent background | Feasibility unestablished |
| --- | --- | --- | --- |
| `:allow` | Accept a checked conditional theorem | Accept the conditional theorem and explicitly record vacuity | Accept the conditional theorem with feasibility unestablished |
| `:report` | Accept a checked conditional theorem | Report a vacuous conditional theorem | Report a conditional theorem with feasibility unestablished |
| `:reject` | Accept a checked conditional theorem | Reject the obligation as vacuous; retain the conditional proof | Leave the obligation incomplete; retain the conditional proof |

These rows assume the conditional statement was independently checked. A native
UNSAT report cannot fill that slot. A rejected or incomplete proof candidate
cannot become an accepted obligation through any vacuity policy. For SAT
questions, a freshly checked satisfying point establishes feasibility directly;
an independent contradiction establishes inconsistency, not a proof query.

`:report` intentionally exposes a conditional theorem without promising usable
premises. `:reject` adds a stronger acceptance requirement, so a caller can
choose nonvacuous contracts without pretending that inconsistency invalidates
classical implication. Use separate result fields rather than overloading one
`:checked` or `:proved` flag.

## Integration order

First run the isolated finite-feasibility experiment: derive the background
from the original graph, prove assertion-byte preservation, check a finite
contradiction or independently replay its witness, and reserve admission/search/
replay before execution. Then qualify an isolated policy composition across all
nine rows, proof failures, insufficient combined allowance, changed assumptions
and saved-record reopening. All evidence must bind the original complete
question, including its exact policy.

Only then change query construction and both graph readers together to accept
exactly `:allow`, `:report`, `:reject`, preserve that choice in the fresh inventory,
and reject other explicit values. Decide missing-field compatibility explicitly:
old defaulted records should continue to mean `:report`; explicit misspellings
should not acquire a new meaning. Keep original record bytes and producer
identities; qualify older packet readers on the next immutable SDK.

The initial policy composition remains a finite Boolean/word capability.
Unbounded integer backgrounds require the graph-native integer kernel and/or a
fresh satisfying point. General String feasibility and ordinary BL execution
need their own semantic connections. None of these judgments proves compiler
preservation or language-wide totality.
