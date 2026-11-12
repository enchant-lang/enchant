# Next: explicit graph references in typed answers and durable verdicts

Design only. The checkpoint-43 graph and opt-in point interfaces do not yet
migrate native answer binding, proof systems or the verdict ledger.

## Preserve meanings before widening capacity

Keep canonical identity v1, native arena IDs, the worker protocol and all
existing typed answer/ledger receipts unchanged. No fallback that silently
converts a failed v1 identity computation into a graph reference. The new
choice belongs to the BL evidence interface, independently of backend choice.
The two backends must still receive the same original question.

A structured question reference contains `:profile` and `:sha256`. Existing
consumers with bare digest fields keep their declared old format. New answer
packets need their own explicit version/profile; use an opt-in constructor
and reconstruct that same declared format during checking. Unknown versions
are refusals, never authority upgrades.

## One complete data boundary

Use the graph checker for all public question fields, including observations,
profiles, scope and origin. Keep exact comparison of canonical bytes where
old binding checked exact canonical contents. A digest alone must not replace
an existing exact-content check. Do not normalize away Int/Float, signed zero,
collection kinds or otherwise inactive context to make a large record fit.

The graph format has separate capacities from the small packet seal. Large
binding vectors and other packet payloads remain bounded by their own declared
format. An existing-only decoder may refuse an unfamiliar keyword; callers
must explicitly admit a bounded vocabulary or retain graph data without
materializing it. Do not create atoms from transport strings to make a test
pass.

## Typed native answer

Bind the actual returned question, original requested question, settings,
result kind and native artifact identity under one explicit answer format.
A native SAT model still needs original assertion replay; observations do not
add assumptions. Preserve `unknown`, `candidate`, unavailable coordinates,
independent replay and backend-reported validation separately. A graph does
not turn a solver's UNSAT claim into a certificate.

Qualify the three-key closure question and a large SAT subject, altered public
context with unchanged formula roots, forged/rehashed references, old saved
answer compatibility, both native backends and a fresh SDK-only consumer.
Native arena ownership and statuses should remain unchanged. No worker change
is justified merely by a language-side identity capacity issue.

## Durable verdict ledger

Keep the previous schema readable. Add an explicitly versioned reference or
record format instead of replacing its old bare question digest. Stored graph
payloads can use the existing bounded blob tier, but the identity and decoder
policies must be explicit. Reopening a row must validate its graph/reference
and reconstruct the original typed answer before any stronger interpretation.
A stored row's assurance remains recorded unless actual independent checks
provide their own evidence.

Recheck saved graph points in a separate pure window with no native query or
Source compilation. Source observation, when requested, happens after that
window and retains actual outcome, input domain, artifact and cleanup scope.

## Remaining foundations

Canonical graph and expansion rules deserve a mechanical model, followed by
a separate implementation connection. The independent mathematical evaluator,
Source specialization/lowering, runtime effects and compiler still have their
own open preservation obligations. Wider term passing supports those efforts;
it does not settle whole-language formality or totality.
