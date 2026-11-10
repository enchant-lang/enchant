# Translation and common-interface qualification

`qualification.json` binds the passing checks to exact source commits, source
hashes, the immutable SDK, the native worker and Z3 library.

- `checks.txt`: 4,432 passing assertions in six files. This includes 244
  translation assertions, 784 certificate assertions, and the existing core,
  contract, loop and API checks.
- `facade-checks.txt`: 481 passing assertions in three files, including 199 new
  common-interface assertions. The 282 API/translation assertions overlap the
  preceding run; do not add the two totals as unique tests.
- `examples.json`: nine closed translation subjects and eighteen native runs,
  complete evidence and a real ANF-derived optimizer example.
- `doc-run.txt` and `doc-check.txt`: nine executable cells, then an unchanged
  recheck of their saved results.
- `browser-audit`: the live dossier at phone and desktop widths, 267 passing
  checks and 24 screenshots. This qualifies presentation and interactions.

The development logs `initial-checks.txt`, `guard-checks.txt`, `load-refusal.txt`
and `path-ledger-checks.txt` retain failed intermediate runs. They exposed partial
native models, missing ground/guard normalization, a load-shape error and the
need to keep explicit unreachable-path evidence. The final passing receipts
above supersede those runs for the qualified implementation.

The gate checks conditional core-model comparisons. It does not establish the
soundness of its implementation, source/compiler preservation, optimized BEAM
emission or production compiler admission. Native solver certificates remain
unchecked; portable certificate objects are a separate path.
