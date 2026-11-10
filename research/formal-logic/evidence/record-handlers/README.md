# Record and source-handler evidence

The record core and source-derived protocol path are now implemented.
`source-check.txt` passed 1,292 assertions across six files: 689 record, 125
source-protocol, 133 existing protocol, 108 bounded trace, 199 facade and 38 API
assertions. `examples.json` retains six source subjects compared with both
engines and separately executed handler-core traces. The safe account is
checked, unsafe/failing/loose-invariant induction premises are refuted, and the
inconsistent initial predicate is explicitly vacuous. A loose invariant's
countermodel is not claimed as a reachable execution.

`model-check.txt` and `Core.olean` retain the separate 42-theorem product/core,
loop and state model. Thirty-seven theorem axiom audits are empty; three use
`propext` and two integer rank proofs use `propext`, `Classical.choice` and
`Quot.sound`. The named-record layout and BL/source/symbolic/model connections
remain unproved. No live actor or production compiler authority is established.

`record-check.txt`, `record-followup.txt` and `record-final.txt` retain initial
failures and the pinned range/variadic-call repairs. `record-qualification.txt`
is the successful 689-assertion follow-up. These overlapping checks must not be
added together as distinct coverage. The combined final run and source/model
receipts identify exact source hashes independently of the original probe.

## Original preparation observations

`probe.json` records five source expressions compiled by the actual pinned SDK
and six direct runtime observations from `handler-probe.bl`. `qualification.json`
binds the script, SDK and observed output hashes. No source-handler verification
implementation or compiler correctness claim follows from these observations.

The runtime probes observe failure in an unselected field of an eagerly built
map, literal field evaluation order in both key orders, ordered `assoc` updates,
selective conditional branches and preservation of other state fields. The
script asserts the field-failure, branch and successful handler observations;
ordering is recorded as observed behavior before choosing record-core rules.

The compiled data exposes ordered `map` pairs, runtime `hash_key` wrappers on
literal keys, remote `get`/`assoc` calls and the function self-application
scaffold. The next implementation must preserve the whole record's outcome
when projecting a field and must recognize actual resolved runtime identities.
