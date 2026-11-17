#!/usr/bin/env python3
"""Replace the dossier's Final numbers section with the round-2 BEAM vs native result."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'native-speed.bl.org'
s = p.read_text()
start = s.index('* Final numbers\n')
end = s.index('* Decisions\n')
section = '''* Final numbers
Integrated stage-1 image =7c32ac57…=: rounds 1 and 2, a 33-namespace
self-hosted closure, 70 units, =(standard-bindings) (extended-bindings)=.

The BEAM side is the integrated SDK =v8jbl8q0…= (descriptor =f748c976…=),
built from the same tree, so both sides run the same reader, compiler, =rt=,
lazy runtime and emitter Source. The protocol is =benchmark/prepare-benchmark.py=:
3 warm-ups, 9 samples × 20 repetitions, median, native then BEAM on the same
host. The emitted Scheme is byte-identical between the two.

#+begin_stats
13.1× | native / BEAM, full pipeline | 11.08 ms vs 0.843 ms
22.5× | read | 1.507 ms vs 0.067 ms
19.4× | compile | 6.685 ms vs 0.345 ms
7.8× | emit | 2.833 ms vs 0.365 ms
#+end_stats

#+begin_src beam-lisp :id final
;; speed/final/evidence-r2/comparison.json (medians, ms).
(def native {:read 1.507 :compile 6.685 :emit 2.833 :pipeline 11.082})
(def beam {:read 0.067 :compile 0.345 :emit 0.365 :pipeline 0.843})
(defn ratio [k] (Float/round (/ (get native k) (get beam k)) 1))
(def ratios (into {} (map (fn [k] [k (ratio k)]) [:read :compile :emit :pipeline])))
(assert (< (:pipeline ratios) 14))
{:native-over-beam ratios}
#+end_src

#+begin_honest :title "Read these numbers with three facts"
BEAM gained from this round as much as native did. Item M removed BEAM's
lazy-cell walk, C2 made emission linear, R rewrote the reader, and T made the
invocation gate a counter read. The integrated BEAM pipeline runs the fixture
in under a millisecond.

Native lost round 1's hand-written Scheme kernel, by design: it now runs
=rt.bl= compiled by its own compiler. KERNEL listed the emitter support that
would make that code tight (boolean =and=/=or=, keyword =case=, direct
self-calls, quoted keyword literals). Those requests are item A.

Self-emission (P) does not yet reach a fixpoint. The image compiles every
Source corpus form, but compiling its own closure stops on the =lower= stub.
#+end_honest

#+begin_rosetta
| Gate | Result | Evidence |
| Integrated SDK | built once, all Nix work on the build station; job =job_65d70b46168ac2f1= | =evidence-r2/build.json= |
| BEAM test batch | 22 of 25 files green; projection preflight 7 of 7 (617 assertions). The 3 failures also fail on main's SDK. | =evidence-r2= receipt, Station thread |
| Host checks | 11 of 11 | =check-host.py= |
| Native closure | 33 units, 0 unresolved remotes, 0 dead leaves, 456 host leaves | =speed/bigo/unresolved-probe.bl= |
| Workstream differentials | reader 11,127 / 0; kernel 42,040 rt rows; lazy 28 / 0; data 692 of 698 (6 outside its files); services 172 / 0; emitter 2,143 / 0 | =speed/*/RESULT.md= |
| Source corpus | =NATIVE_COMPILER_SOURCE_CORPUS_OK=, 0 FAIL, identical to round 1 | =evidence-r2/source-corpus.log= |
| Emitted Scheme | byte-identical native and BEAM | =evidence-r2/comparison.json= |
| Not run, or open | actor corpus; stage 2 = stage 3 (P) | =evidence-r2/stage2-emit.log= |
#+end_rosetta

'''
s = s[:start] + section + s[end:]
p.write_text(s)
print('ok')
