# The live formal logic review

The canonical document is [ATLAS.bl.org](../../ATLAS.bl.org), served at
<https://work.tailcb5318.ts.net:18100/>. Its fully formal language chapter is
`#s-could-beam-lisp-be-fully-formal`. This presentation extends the retained
standalone atlas; it does not replace its historical evidence.

The chapter distinguishes formal semantics from totality, partial from total
correctness, and solver results from checked proof objects. It discusses a
small pure core, explicit effects, macros and tactics whose output is checked,
dynamic boundaries, actor traces and fairness, proof system choices, compiler
preservation and translation validation, bootstrap trust, and the limits of a
specification. The recommended first slice is one integer contract connected
to resolved ANF and a narrow independently checked proof system. The kernel
and verified compilation remain proposals.

The presentation uses 39 semantic block families plus source cells, including
the kit's new claims ledger and lifetime timeline. Screen coverage in the
ledger means a view exists; it does not measure logical proof coverage. The
timeline assumes a future checker and uses illustrative dates. The source
explorer discovers three annotated public BL renderers and calls those same
functions for its examples and the five retained-evidence views.

## Recorded evidence

- [browser-audit/audit.json](browser-audit/audit.json): 233 passed browser
  checks at 390px and 1440px, with 22 screenshots. It exercises source previews,
  the claims dialog, lifetime selection, milestones, all 14 connected review
  graphs, maps/Back/fullscreen/Escape, themes, witness frames, source discovery,
  route refusal and anonymous write refusal. It checks the live presentation,
  not the truth of language theorems.
- [feedback-audit/audit.json](feedback-audit/audit.json): ten passed checks on
  a disposable loopback dossier with a fixed test identity. They cover failed
  writes, explicit authorized saves, reload, draft and selection preservation
  across live refresh, no automatic save and anonymous refusal. No review was
  submitted to the canonical dossier; the fixture and test service were removed.
- [witness.json](witness.json): five actual Scenario Runner browser claims.
  [walkthrough/run.json](walkthrough/run.json),
  [walkthrough/film.json](walkthrough/film.json), and twelve PNG frames retain
  that run. These are recorded interactions, not proofs of BL semantics.
  No movie was exported; the film block declares this gap.
- Three executable dossier cells exercise the actual shared solver interface,
  distinguish a language outcome from a model bound, and show unchecked
  certificate status. `bl doc run` generated their stored results.

The older 795 assertions and 187 backend questions remain in the parent
evidence directory with their original scope. Presentation checks add no
backend qualification, production semantic change, proof kernel or SDK build.

## Running and retiring the review

From the integration checkout:

```sh
research/formal-logic/review cells
research/formal-logic/review check
research/formal-logic/review serve
research/formal-logic/review url
research/formal-logic/review stop
```

The launcher verifies the immutable SDK descriptor in
[sdk-pin.json](../../sdk-pin.json), caps checks and uses the local
`~/projects/enchanted-skills` kits. The requested live deliverable is managed
as `work-enchant-formal-review.service`, with a 1GB memory cap. This integration
session owns it. `review stop` retires it; all test browsers and temporary
feedback services are disposed after their checks.

Owner identity comes from the operator's service environment and authenticated
tailnet header. Saved answers and task notes patch the canonical Org source
explicitly. Anonymous readers can inspect the page but cannot save feedback.

[delivery.json](delivery.json) records the handoff state and observed source
hashes. The kit is a shared development checkout: its source snapshot records
what was on disk at handoff, while the live process loads BL modules at startup
and reads CSS/JavaScript on request. This is a development preview, not an
immutable deployment of the kit.
