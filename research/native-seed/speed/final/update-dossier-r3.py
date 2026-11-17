#!/usr/bin/env python3
"""Round 3, wave 1: roster outcomes and the round-3 numbers in the dossier."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'native-speed.bl.org'
s = p.read_text()


def done(head, outcome, keyword='DONE'):
    global s
    old = '** TODO ' + head
    assert old in s, head
    i = s.index(old)
    j = s.index(':END:\n', i) + len(':END:\n')
    s = s[:i] + '** ' + keyword + ' ' + head + s[i + len(old):j] + '*Outcome (round 3).* ' + outcome + '\n' + s[j:]


done('A3 · Attribute the gap on a real corpus',
     'MEASURE: reader.bl (104 definitions) through read, compile and emit. Native: compile '
     '82.5 %; top costs the compiled kernel (15.8 %), bl-invoke resolution of variadic calls '
     '(12.3 %), a struct test that materialised a set (10.9 %) and a quoted special-forms set '
     'rebuilt per node (10.2 %); ticks under 0.1 %. BEAM: the invocation gate (17.2 %), generic '
     '=, variadic tuple/list. Both one-site items were fixed in this wave '
     '(=speed/attrib/RESULT.md=).')
done('P3 · Self-emission fixpoint',
     'The native image rebuilds itself: stage1 compiles its own 34-namespace bundle inside the '
     '240 s deadline, stage2 = stage3 byte for byte, and the Source corpus agrees on all three '
     'stages (=evidence-r3/source-fixpoint.json=, actors not run). Native self-emission equals '
     "BEAM's stage1 line for line after renaming gensym locals. It took four fixes: every "
     "member compiled against the image's own link rows and core's (=member-rows.bl=), "
     'bounded link-row batches (gsc timed out on one 439 KB form), NIF counterparts reaching '
     'sealed local calls, and set/map literals in term order.')
done('X · Actor corpus and cross-process lazy waits',
     'ACTOR: a force on a cell another actor is evaluating now WAITS on both targets, as on '
     'BEAM; a two-actor wait-for cycle still raises. Native corpus at the default budget: 461 '
     'checks identical to round 1 (gsi). Open: budgets 17 and 41 and the compiled-ELF run '
     '(FRAMES moved turn boundaries), and the JS baseline.', 'NEXT')
done('N1 · Kernel emitter forms',
     'BACKEND: boolean junctions, keyword case, direct self-calls and keyword constants, then '
     'sealed direct and variadic calls, literal arity cells (1,542 definitions) and every '
     'constant literal hoisted. rt unit: 1,185 string->symbol calls to 0, 51 self-call tests '
     'to 0. Every emission difference reduces to a named transform (=speed/backend3=).')
done('N2 · Multi-arity rt fast paths',
     'BACKEND: nth, k-nth and conj answer a list or vector inline; 6,636 new differential rows '
     'equal BEAM.')
done('N3 · Sealed direct links',
     'LINK: the native closure is sealed (cells defined once, redefinition refused); BEAM has '
     '=Env/seal!= for releases, not yet called by any release build. Dev images unchanged.')
done('N4 · Frames and budget sites',
     'FRAMES: ticks at loop heads and at entries of functions that can call BL code (rt: 1,275 '
     'to 586); debug frames from per-site constants (4,454 per-call frame builds to 171). '
     'Turn counts per budget change; see X.')
done('E1 · One fact pass, two backends',
     'FACTS: one conservative fact pass inside =BeamLisp.Optimize= (no new floor member) feeds '
     "the BEAM optimiser and native emission. Output byte-identical on rt, reader and "
     'warm-core; 28 functions validated against formal.elaboration/check, 0 violations, 9/9 '
     'wrong facts caught.')

anchor = '** TODO V2a · Gambit immediates and interned keywords'
assert anchor in s
s = s.replace(anchor, '''** DONE Q3 · Value-equality collection keys
:PROPERTIES:
:AREA: semantics
:TARGET: both
:END:
*Outcome (round 3).* KEYS: two keys are the same key iff they are =; each key is
stored as one canonical representative (=speed/keys/DECISION.md=), so
=(get {1 :x} 1.0)= is =:x= on both targets and raw Erlang map functions stay
exact. Sorted collections order every number numerically.

''' + anchor, 1)

start = s.index('* Final numbers\n')
end = s.index('* Decisions\n')
s = s[:start] + '''* Final numbers
Round 3, wave 1. Integrated SDK =mp370y60…= (descriptor =a99a1534…=) on both
sides; a 34-namespace sealed closure that rebuilds itself (stage2 = stage3).
Protocol unchanged: 3 warm-ups, 9 samples × 20 repetitions, median, native
then BEAM on the same host. The emitted Scheme is byte-identical between the
two. The host was loaded (load average 11 to 15); native is stable between
runs, BEAM is not, so two runs are kept and the slower-ratio one is quoted.

#+begin_stats
7.5× | native / BEAM, full pipeline | 8.82 ms vs 1.17 ms (round 2: 13.1×)
8.7× | read | 0.572 ms vs 0.066 ms (round 2: 22.5×)
12.2× | compile | 4.581 ms vs 0.376 ms (round 2: 19.4×)
6.8× | emit | 4.130 ms vs 0.610 ms (round 2: 7.8×)
#+end_stats

#+begin_src beam-lisp :id final
;; speed/final/evidence-r3/comparison.json (medians, ms).
(def native {:read 0.572 :compile 4.581 :emit 4.130 :pipeline 8.817})
(def beam {:read 0.066 :compile 0.376 :emit 0.610 :pipeline 1.172})
(defn ratio [k] (Float/round (/ (get native k) (get beam k)) 1))
(def ratios (into {} (map (fn [k] [k (ratio k)]) [:read :compile :emit :pipeline])))
(assert (< (:pipeline ratios) 8))
{:native-over-beam ratios}
#+end_src

#+begin_honest :title "Read these numbers with three facts"
Native moved by itself this round: the pipeline went from 11.08 to 8.82 ms,
read from 1.51 to 0.57 ms, compile from 6.69 to 4.58 ms.

BEAM's pipeline is slower than round 2 (0.84 to 1.17 ms), almost all in emit
(0.37 to 0.61 ms). Emit here is the native Scheme emitter running on BEAM,
which now analyses tick sites, facts and constants per node; it is not BEAM's
own code generation. The other run on this build measured 4.7× (BEAM 1.73 ms).

The actor corpus has not run on the compiled round-3 image (item X).
#+end_honest

#+begin_rosetta
| Gate | Result | Evidence |
| Integrated SDK | built once on the build station; 52 of 55 focused files green, the 3 failures identical on the round-2 SDK | =sdk-pin.json= |
| Host checks | 12 of 12 stages | =check-host.py= |
| Native closure | 34 units, 0 unresolved remotes, 0 dead leaves, 462 host leaves | =speed/bigo/unresolved-probe-r3.bl= |
| Self-hosting | stage2 = stage3 byte-equal; Source corpus equal on stages 1–3 | =evidence-r3/source-fixpoint.json= |
| Native vs BEAM emission | equal line for line after gensym renaming | =speed/final/compare-stages.py= |
| Emitted benchmark Scheme | byte-identical native and BEAM | =evidence-r3/comparison.json= |
| Not run | actor corpus on the compiled image; JS baseline | item X |
#+end_rosetta

''' + s[end:]

old_status = s[s.index('#+status: '):s.index('\n', s.index('#+status: '))]
s = s.replace(old_status, '#+status: Round 3 wave 1 integrated · native rebuilds itself (stage2 = stage3) · native 7.5× warm BEAM on the pipeline (was 13.1×)')
p.write_text(s)
print('ok')
