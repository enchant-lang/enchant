# Source-handler preparation observations

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
