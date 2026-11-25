# Native compiler roster: revisit

These are results that disappointed. Each one either missed its target, moved
its cost somewhere else, or measured no better than noise. They are kept here so
that a later round can take them on together, starting from what was learned,
instead of rediscovering them one card at a time. The live plan is in
`ROSTER.md`; the full card text and batch notes are in `ROSTER-archive.md`.

Opened 2026-11-25. Each entry gives the target, what was measured, why it fell
short, where the branch or evidence lives, and what a second round would try.

## How to run a revisit round

- **Pick entries that share a cause.** Several entries here bottom out in the
  same few costs:
  - the per-load SDK runtime inventory, about 100–200 ms per load after the lease;
  - compiling a unit three times (an eval module, a per-defn body module, then the final emit);
  - the daemon namespaces loaded one by one at VM start.
  One change to one of these can move three entries.
- **Measure before and after in one session, interleaved,** with `m1.py`. Our
  rule from batch 28 onward: a row that only got faster at a different load is
  not a result.
- **Each entry needs a `priv/host` or `priv/boot` SDK build to prove.** So a
  revisit round should wait for N4d, which brings a host edit down to about
  3 minutes. Until then each attempt costs a 30–40 minute gate.

## Entries

### M3b — the first command in a fresh checkout VM (cost moved, not removed)
- **Target (M3).** `first-in-fresh-vm/test` ≤ `cold/test` in `m1.py`.
- **Measured.** Branch `lane/m3b` (`7b827d070`, `07166f035`), evidence in that
  branch's `research/checked-tiles/evidence/m3b-first-command.json`. With no VM
  serving the tree, `test` and `check` run cold at once and the VM starts beside
  them. The first command goes from 6.1 s to 3.32–3.66 s, about cold + 120–210 ms.
  The second command then pays the fresh VM's first-request work: about 1.1 s with
  the pre-warm emulated, against 0.14 s before. The first two commands take about
  4.5 s either way (3.35 + 1.15 against 4.61 + 0.14).
- **Why it falls short.** About 0.9 s of a fresh VM's work is daemon
  infrastructure that `--cold` never runs: the session, the manager start, the
  owner registry (`vm.owner` replays `proc.reg`), `reload.generation`, realm open,
  `bl.daemon` and the overlay sync. Then the SDK lease walks the whole closure
  (`retain_sdk_runtime!`, 754–859 ms warm), and every later SDK load re-walks it
  (166–216 ms). Cold-first hides that work from the first command but does not
  remove it.
- **Not merged.** It is not a net win for a VM that serves more than one command.
  It also changes the client's transport choice (`COLD_FIRST_VERBS`), and
  `vm.session`'s pre-warm can only be checked on an SDK built from the branch.
- **Second round.**
  - Remove the work instead of moving it: seal the daemon namespaces' initial
    state into the boot image, K1-style.
  - Make the lease incremental, so each SDK load patches the inventory instead
    of re-walking it. That is the same cost as the library-edit card, so do that
    card first.
  - Then decide whether cold-first is still worth having. If the fresh VM's
    first command is close to cold by then, drop it.

### E1 — the compile of the one edited unit (partly done)
- **Target.** Body edit then test ≤ 200 ms; a `priv/lib` edit ≤ 600 ms.
- **Measured.**
  - Body edit then test: 300 → 239 ms.
  - Unchanged warm test: 115 → 67 ms. The cause was the test file loading
    outside a declaration pass (`d6a1ab316`, batch 30).
  - A library edit is unchanged at about 850 ms.
- **Why it falls short.** Every remaining cut is in `priv/host` or `priv/boot`,
  so none could be measured without an SDK. The agent dropped its one host change
  (remembering `source_path` within a pass in `loader.bl`) as unproven.
- **Profile, for the second round (raised stack depth, `/tmp/e1-othman/prof/`).**
  - Library edit then run:
    - OTP compile 29%, about 60 `compile:forms` per edit, half of it in `beam_ssa_opt`;
    - `load_unit` 14%: each `defn` is compiled three times;
    - recompiling project units 13%;
    - inventory patch 6%;
    - `retain_sdk_runtime!` 4.4%.
  - Body edit then test: `Reload.Check` 7.5%, realm drain 5%, code purger 5%,
    `Tiers/priv_root` 4%.
- **Second round.** The library-edit card in `ROSTER.md` takes the library half.
  For the body half:
  - remember `source_path` per pass;
  - cache `Tiers/priv_root`;
  - run a literal-argument `Link/defvar` form directly instead of compiling an
    eval module. It must keep the stack frame that error messages use to name the
    failing form.

### F3 — the warm request floor (4.7 ms, target 2 ms)
- **Target.** A warm unchanged request ≤ 2 ms median on a quiet machine.
- **Measured.** Batch 26, at load about 5:
  - `.bl/bin/bl`: 4.7 ms;
  - `./bin/bl`: 6.6 ms;
  - `run_file` on an unchanged file: 0.43 ms of that.
- **Why it falls short.** Each request runs a fresh client process, and it
  connects, says hello, and sends about 91 environment variables. A request that
  costs nothing is still a process start plus a socket round trip.
- **Second round.** Add a resident client or broker that keeps the connection
  across processes. Send an environment generation instead of the variables, which
  is a protocol bump. Measure against `.bl/bin/bl`, not `./bin/bl`.

### K1b and init — cold `bl run` (1.05 s, target 0.8 s)
- **Measured.** Cold sealed `bl run`: 1.04–1.07 s (batch 26). The rest needs
  design decisions:
  - **Initializers: 226 ms.** `mark_emitted` receipt compression is 84 ms of it.
    Storing receipts uncompressed saves about 45 ms and costs about 3 MB per VM.
    That trade-off is the user's call.
  - **Attribute decoding of the phase library: 46 ms.** This is a `priv/boot`
    emitter change.
  - **The floor proof: 52 ms.** It could be sealed in `do-prime`.
  - **erts and Elixir: about 240 ms.** The `elixir -e :ok` floor alone is 190 ms.
- **Second round.** Take these as one card once N4d makes boot and host edits
  cheap to try.

### M2 — project units restored across realm retirement (target revised)
- **Original target.** A body edit's first command ≤ 200 ms, with only the edited
  namespace recompiled.
- **Measured.**
  - An unchanged realm restores: 285–310 → 170 ms.
  - The first `run` after a body edit got 55 ms faster.
  - `body/first/test` was unchanged at about 290–335 ms, because that row loads
    only the edited unit, and that unit's compile (80–150 ms) is the floor.
- **Also.** `compile_source` is about 1.8× the eval path on real units, so a
  first sighting still takes the eval path and stores nothing. A unit is stored
  only when its key is asked for again.
- **Second round.** This shares a cause with E1: the same compile done three
  times. Once `compile_source` is no slower than `eval_string`, store on first
  sight.

### N0 — the native front end (no-go)
- **Target.** Native ≥ 2× the BEAM per unit, before N3, N5 or C3 go ahead.
- **Measured.** 1.86× *slower*: 350 s native against 256 s on the BEAM over 667
  units. The median unit takes 317 ms native against 185 ms on the BEAM
  (`research/checked-tiles/evidence/n0-native-vs-beam.json`).
- **Why.** The native compiler's slowness comes from its generic map, invoke and
  byte-list representation, not from a lack of native code. The 158 ms "warm
  BEAM" baseline it was first compared with was the emitter on one file, a path
  the product never runs.
- **Second round, only on new evidence.** C3 (typed private IR) is the only
  candidate that attacks the cause. Reopen it only with a prototype that measures
  ≥ 2× on real units.

### C2 and the U7 prototypes — measured as noise
- **Results.** These prototypes moved their target by less than noise:
  - C2 interned names: 0.4%.
  - U7 batch preload: no change; loading is about 4% of a cold start.
  - U7 `find_file` memo: at most about 1%.
  - "something compiles": nothing compiles on an unchanged SDK.
- **Detail.** The full findings are in `ROSTER-archive.md`, under "Prototypes kept, not merged".
- **Second round.** None as they stand. They are listed so that nobody
  re-measures them.
