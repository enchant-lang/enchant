# Give fixed-width words an explicit replay resource policy

The standalone project prototype passed **3,526 assertions** on the selected
retained-request SDK. The [qualification](evidence/word-resource-prototype/qualification.json)
binds the actual source commit, immutable SDK, capped commands, complete green
summaries and resource cleanup. The planner file accounts for 3,476 assertions;
the graph coordinate reader accounts for 50.

Planner prototype v2 refuses excessive declared widths before forecast
arithmetic. Its earlier v1 qualification remains under
`before-early-width-admission/`; the current checks add an existing 8-KiB width
integer, full shape validation before refusal and unchanged valid forecasts.

The planner describes the existing SDK word operations with an exact input
reference, normalized limits, a ready/incomplete decision, result width,
intermediate width and a work charge. Invalid arity, sort relations, extraction
bounds and extension data refuse. Unknown operations remain unsupported. The
checks compare planned result bounds with actual SDK term evaluation across
widths one through eight and boundary bit patterns, and check selected temporary
arithmetic sizes. They also cover exact limits and a billion-bit declaration
refused using small metadata arithmetic.

The coordinate reader recognizes the exact reserved word wrapper in the original
flat graph. It refuses nonpositive width, negative bits, overflow, wrong numeric
kinds and malformed wrappers. A bounded right shift tests the already-present
bits without constructing a power or mask. Work reservation includes an upper
bit count from the integer's encoded size, so a tiny declared width cannot hide
a huge invalid input. Aggregate coordinate charges have explicit boundaries.
Unfamiliar application keyword names stay graph cursors; a repeated warm read
preserves the atom count, and explicit attempted materialization still refuses.

These are project prototypes under `prototypes/word-resources`, outside the SDK
and ordinary research import path. Their ready plans and diagnostic outputs are
ordinary data. They do not establish a checked point, grant an execution lease
or extend the managed request profile. Their charges are policy conventions,
separate from whole-graph capacity and actual BEAM cost. The check program uses
existing SDK term semantics; it is not a paired-native qualification or an
independent mathematical implementation.

The separate [word-envelope model](WORD-ENVELOPE-MODEL.md) establishes modular
arithmetic magnitude bounds with an audited assumption ledger. It does not
prove these BL implementations or bit-mask/signed semantics. The [integration
plan](WORD-PROFILE-PLAN.md) moves checking into the actual point's shared account,
keeps existing numeric/retained contracts and defines the next immutable SDK
batch. The wider formal/total language goal remains active.
