#!/usr/bin/env python3
"""One-shot dossier update for round 2: roster statuses, P status, S item, A retarget."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'native-speed.bl.org'
s = p.read_text()


def done(head, outcome):
    global s
    old = '** TODO ' + head
    assert old in s, head
    i = s.index(old)
    j = s.index(':END:\n', i) + len(':END:\n')
    s = s[:i] + '** DONE ' + head + s[i + len(old):j] + '*Outcome (round 2).* ' + outcome + '\n' + s[j:]


done('C2 · Restore emitter throughput',
     'BACKEND: the emitter builds no lazy sequence and joins text with two small helpers; one '
     'loop-verdict walk per region. 2,143 emitter comparisons and all 1,394 closure definitions '
     'are byte-identical.')
done('B2 · BL kernel in rt.bl',
     'KERNEL: the native kernel is =rt.bl= compiled by the native compiler. All 34 Scheme overrides '
     'and =kernel-override= are deleted. Hot rt functions became inline type tests, and literal '
     'equality templates emit =eq?=/=null?=. Native differential: 42,040 rt rows equal BEAM; the 77 '
     'that differ are identical to the original rt.bl native answer.')
done('M · Lazy cells without a capture walk',
     'LAZY: the BEAM walk is gone. Cycles are detected at force time: a re-entrant owner, a '
     'cross-process wait-for chain, or a completed-alias chain. A value that contains its own node is '
     'now data. Lazy is compiled natively from =lazy_memo.bl=, =lazy_seq.bl=, =seq_cursor.bl= and '
     '=deferred.bl=; =host-lazy.scm= is deleted, and =native-memo.scm= is only the NIF counterpart. '
     'BEAM lazy suites are green on the integrated SDK.')
done('D · Compile is a function of source',
     'FRONT: an aliased call into a declared, not-yet-loaded namespace links from its source, not '
     'load state. =incr.bl= on the integrated SDK: 0 of 84 identities change on an unchanged or '
     'comment-only re-analysis. Not covered: boot-tier stubs (see P).')
done('R · Byte-class reader',
     'READER: a per-codepoint automaton of inlined BIF steps (the charlist stays, because native '
     'text is codepoints). 11,127 differential checks over 1,021 files and a 103-case error corpus: '
     '0 mismatches. Reader tests are green.')
done('U · Content-addressed units',
     'BACKEND: a unit ends only after a whole definition, at name-hash cut points, and keys exclude '
     'the ordinal. 40 of 40 random edits change exactly one of 58 units. Stage 1 is now 70 units.')
done('T · Link-time invocation on BEAM',
     'FRONT: the gate is a counter read when no Source extent is live. Natively the count is a '
     'constant zero cell, the same decision the deleted override made.')

old = ('closure explicitly with =native.intrinsics= and move the linking context into\n'
       '=native.eval=.\n')
assert old in s
s = s.replace(old, old + '''*Status (round 2).* CLOSURE moved the whole linker into =native.bootstrap=,
shared by the BEAM driver and self-emission. On BEAM both paths emit
byte-identical Scheme for sugar, server-clause and reader-node. On the real
image, =stage1 --compile= fails after 59 s: /native resolution: global
context namespace absent from closure (lower)/. On BEAM, =lower= is loaded,
so =compiler.bl='s calls into it compile as module-linked remotes, which link
as an excluded stub. In the native image =lower= is not loaded, so the same
source compiles to =:global= references. This is item D's class of bug for a
boot-tier stub. Next: the native Env answers =lower='s link rows exactly as
BEAM does, then one image build to show =stage2.scm= = =stage1.scm=.
''')

anchor = '** DONE M · Lazy cells without a capture walk'
s = s.replace(anchor, '''** DONE S · No host Scheme replicates a BL file
:PROPERTIES:
:AREA: self-hosting
:END:
Host Scheme may only be the native counterpart of something with no BL
source: the term model, Erlang BIFs and Elixir stdlib, a NIF, or the OS
(=speed/CONTRACT2.md=). The integrated closure has 33 namespaces, 14 more
than round 1. They now include =host.lazy-memo=, =host.lazy-seq=,
=host.seq-cursor=, =host.deferred=, =host.delay=, =host.sorted=,
=host.ex-info=, =host.compile-error=, =host.emit=, =host.link=,
=host.server=, =host.compiler=, =native.intrinsics= and
=native.resolution=. Every remote links (0 unresolved), and the build reports
0 dead leaves.

*Residual replicas*, each with its owner's reason:
- Vector, Set: need V2's representation;
- Num, Decimal (and =native-decimal-parse=): about 20 stdlib leaves and the
  regex FFI;
- Transient: compiles, but has no differential yet;
- Refs, Multi, Reactive: depend on Env and Task;
- Record: =persistent_term= class publication;
- =Tiers/boot_namespaces=: should come from bundle metadata.

The Env, AOT and Loader leaves are native services, not replicas.

''' + anchor, 1)

old = 'Read is still 15.5× and compile 12.2×. Re-instrument the linked image at'
assert old in s
s = s.replace(old, '''Round 2: read 22.5×, compile 19.4× and emit 7.8× against the integrated
BEAM. Candidates, in order:
- the compiled kernel, through KERNEL's requests to BACKEND: boolean
  =and=/=or=, keyword =case=, direct self-calls, quoted keyword literals;
- entry ticks;
- V2.

Re-instrument the linked image at''')

old_status = ('#+status: L, K, V, C integrated · native within 2.8× of warm BEAM on the pipeline '
              '(was 35×) · big-O study adds M, D, R, U, T')
assert old_status in s
s = s.replace(old_status, '#+status: Round 2 integrated (M, D, R, U, T, C2, B2, S) · self-hosted closure of '
              '33 namespaces · native 13.1× warm BEAM on the pipeline · P open')
p.write_text(s)
print('ok')
