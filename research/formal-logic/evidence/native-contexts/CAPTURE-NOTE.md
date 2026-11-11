# Retained browser capture discrepancy

The complete browser audit passed 1,075 checks initially and 1,077 after adding
a topic visibility assertion. Two extended-run phone frames omit glyphs in the
native context inspector topic bar. Waiting for font readiness and two paint
frames did not establish a complete fix.

A fresh direct probe and the same full audit prefix both produced readable
topic glyphs. The prefix also records correct colors, visible geometry and
pointer hit targets in `browser-owner-diagnosis/owner-nav.json`. It stops
deliberately after that panel, so its `audit.json` is a diagnostic stop rather
than a failed implementation qualification or a complete browser audit.
Its exact probe source is retained as `browser-owner-diagnosis/probe.mjs`.

The final visual review retains this limitation explicitly. It does not claim
a persistent product navigation defect or a resolved headless capture issue.
The implementation tests and 41 reproducible executable cells are independent
of this discrepancy. No product CSS or renderer change was made from this
uncertain capture evidence.
