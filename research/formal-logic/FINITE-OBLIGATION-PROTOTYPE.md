# Conditional proof, feasible premises, and caller policy

The isolated `prototypes/finite-obligation` experiment is prepared and has not
run. Its runner requires the scalar SDK to be qualified and selected and the
separate finite-feasibility experiment to pass first. It changes no SDK code.

`formal.finite-obligation/check` accepts the complete original request and a
finite-word certificate candidate. It freshly checks conditional entailment,
optionally runs the complete background feasibility strategy, then applies the
exact original `:vacuity` field according to `VACUITY-SEMANTICS-REVIEW.md`.
No producer-supplied check result is an input. Its result retains three distinct
fields: `:entailment-check`, `:feasibility-check`, and `:policy-check`.

This prototype deliberately reads the original policy bytes. The selected SDK's
older graph executor still collapses non-`:allow` policies to `:report`; that
must be changed and qualified as a later coherent runtime batch. Missing policy
means `:report`; an explicit unknown or ill-typed policy is refused here.

The caller supplies `{:work-units n}`. Fewer than 3,300,000 units invokes neither
checker. At 3,300,000, conditional proof checking is reserved but feasibility is
not run. At 6,900,000, both complete strategies are reserved before invocation.
The account describes policy units, not a proved CPU or allocation cost. This
allows an independently checked conditional theorem to remain useful while a
stronger nonvacuity requirement is still incomplete.

`pack` stores the original request and candidate only. `reopen` rechecks them
under the reader's current allowance; a saved producer result or limit is not
accepted. This isolated packet format has no durable ledger integration and no
authentication or native execution authority.

The six prepared tests cover all nine policy/feasibility combinations using
actual checker calls, malformed candidates under every policy, prospective
proof-budget refusal with a calibrated invocation trace, changed policy and
assumptions, solver/oracle-denied execution, and saved packets reopened with a
smaller current allowance. The planned complete run has at least 93 assertions, including the common
ordinary-value/raw-node policy parser and missing-versus-explicit-nil behavior.
A passing same-process packet test alone would not qualify fresh-process
schema vocabulary or durable storage; those remain explicit later gates.

There is no Source, compiler or mechanical soundness theorem in this prototype.
