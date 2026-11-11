# A solver worker in the SDK

The term interface needs a native worker without a research checkout. The
packaging slice moves the canonical term worker into `native/ports/formal_worker`,
builds it as its own pinned executable artifact and carries it in the SDK's
`priv/formal` directory. It remains a port worker, separate from NIF libraries.
The original text-worker experiment retains an explicit compatibility entry.

Ordinary `formal.logic/run` calls should select packaged worker and Z3 library
paths from the running language image. Explicit options and existing research
environment overrides remain available and identified separately. No system
PATH lookup selects a solver. Complete questions, native ownership, deadlines,
typed replay and proof authority rules remain unchanged.

The artifact records its source, Cargo lock, enabled solver features and actual
worker bytes. Runtime evidence names the files actually used. Portable
packaging rewrites ELF files, so its manifest must describe the resulting bytes
and retain the producer identity separately. A producer hash cannot stand in
for the relocated executable's hash.

The selected SDK passes 503 assertions across eight focused files, including
42 artifact checks and 11 selected Source checks. The twenty-two-file formal
regression passes 7,086 assertions. All 187 preceding paired question identities
and backend verdicts are unchanged. Both ordinary backends also run from an
unrelated temporary directory without research imports or artifact environment
variables. The preceding SDK fails the six unconfigured-call assertions.

```clojure
(ns ordinary (:require [formal.term :as t] [formal.query :as q]
                       [formal.logic :as logic]))
(def x (t/variable "x" t/Int))
(logic/run {:backend :oxiz}
  (q/sat {:assumptions [(t/eq x (t/int 7))] :observe {"x" x}}))
```

Change `:oxiz` to `:z3` to ask the same term question through the other adapter.
`formal.backend/artifacts` inspects the actual selected paths, hashes and
origins without starting a solver. Options take precedence over environment
pins, followed by this running image's defaults. A mixed selection identifies
which components actually use the packaged descriptor. It never searches PATH
or guesses an executable from the application's current directory.

The portable product packages this same SDK image. Its observed application
run on this host uses the relocated files outside the Nix store, with an FHS
ELF interpreter and no RPATH/RUNPATH. Both backends return seven with valid
replay and prove the integer increment claim. The runtime descriptor retains
the native producer hashes and records the changed portable bytes separately.
The initial observation helper searched the wrong cache directory after the
application succeeded; its correction reads the actual runtime path recorded
by that application. This is host execution evidence, not a clean-host
activation rehearsal, release publication or rolling-release qualification.

The canonical source preserves all 104 registry dependency pins and explicit
OxiZ std features. The legacy experiment's two binary targets pass Cargo's
locked offline check against the delegated canonical library; it uses a private
target directory. Its preceding qualified release binaries stay untouched.
Build memory values in the native descriptor describe the artifact-construction
guest. Runtime requests retain the existing owner, deadline and caller resource
limits.

Read [the SDK-only example](packaged-worker-check.bl), [its native result](evidence/packaged-worker/examples.json),
[the portable result](evidence/packaged-worker/portable-examples.json) and
[the qualification](evidence/packaged-worker/qualification.json).
Packaging does not migrate the default legacy text oracle, add solver theories,
establish compiler preservation or prove totality.
