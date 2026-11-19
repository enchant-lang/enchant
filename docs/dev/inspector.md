# Development inspector

Start a Live app with `bl serve app.bl` to show the collapsed dock to
developers. The app supplies the authorizer to `live.app/serve`:

```clojure
(app/serve application
  {:port 4040
   :devtools {:authorize developer?
              :work {:imports imports-owner}
              :projections {:totals totals-reader}}})
```

`developer?` receives the app's resolved principal and must return exactly true.
Use `{:devtools false}` in the project's `env.bl` to disable the inspector for
all its `bl serve` launches. Use `--no-dev` for one launch or `:enabled? false`
for one listener. The project's `:loading` declaration chooses the environment
variable and production values. The defaults are `BL_ENV=production` and
`BL_ENV=prod`. The setting applies to listeners started directly by the entry
program. The app supplies the principal check.

The portable `bl` drop defaults `bl serve` to development when `BL_ENV` is
unset. The collapsed dev button uses the same app authorizer as the SDK.

An application OTP release launcher sets `BEAM_LISP_IMAGE=release` and defaults `BL_ENV`
to `production`. Live keeps the dock off in that image. A Nix SDK selection
is a development-capable toolchain and supplies its exact immutable identity
to the panel. Programmatic starts outside `bl serve` can opt in with
`:enabled? true` and an authorizer.

Unauthorized viewers receive the original screen and a 404 for assets and
snapshots. Existing HTTP handlers still compose. `app/stop!` releases the
listener, internal shared connection and inspector reader.

The injected dock shows page updates, Loom spacing/colours/corners, real tool
activity and registered owner status. The left Enchant button opens and closes
the panel. Server shows the serving VM's Beam Lisp and Erlang/OTP versions and
counts running jobs across all registered work owners, including jobs outside
the visible list. Server can copy the SDK identity, timings and counters in a
report that omits subjects, paths, symbols, source text and runtime handles.
Select a projection status in Server to open its latest decision. The receipt
links a publication to its admission and earlier decisions. Tool detail has a
Receipt link to its recorded operation. Receipts use the same authorization as
the Inspector and expire when the owner discards them.
Click an update to inspect its server render. Click a tool run to see cache
computations, reuse, recorded admission waiting and child runs. Elapsed time
outside admission wait is wall time. Cache bytes and evictions describe
confirmed admissions in that run. The reason identifies source changes or a
new definition revision. Named providers appear when their observed
generations differ. An app can supply `:source-link (fn [principal location] ...)`
to link a relative source reference to a same-origin editor route. The default
action copies the path. Function labels come from actual analysis
worklist evaluations, with sixteen labels retained. They are not a complete
function list. Check always runs house rules, including when compiler facts
are reused. Browser update counts count patch operations, not CPU usage.

Authorized app screen/intent callbacks retain the host tape across HTTP/OTP
callbacks. This changes telemetry attribution only; it never rebinds execution
authority or overrides an explicitly different realm.

Activity records instrument `lsp/analyzed`, `bl.check/analyze-source` and
`codebase/index-source`. They stay in the caller's environment and VM scope.
In a project with an `env.bl`, the Nix SDK routes ordinary `serve`, `check`
and `codebase` commands through the project runtime. Run the commands from
two terminals in that project. Explicit transport flags and the project's
`:warm` setting take precedence. A CLI command using the serving runtime
appears with a CLI label.

```sh
bl check --quick src/app.bl   # reader errors and repeated definitions
bl codebase src/app.bl        # top-level definitions and direct imports
```

The quick commands read one regular `.bl` file of at most 64 KiB. They share the
parsed summary by exact source and reader revision. The outline reports totals
and shows up to 32 definitions and imports. Full `bl check FILE` provides
compiler diagnostics and house rules.

Development listeners watch the served entry file’s directory for saves.
A quiet window folds repeated filesystem events into one check. Only regular
`.bl` files within the quick tools’ size limit are read. Refresh the page
after a save. An error marks the existing Tools button and selecting it opens
the run at the reader’s reported line. A corrected save clears that file’s
mark on refresh. The dock derives its marker from the latest retained runs.

No observer starts an editor request, check, index, projection subscription or
worker. A hidden/closed dock has no polling; an open Tools/Server panel allows
one request at a time with an abort deadline. Browser history caching pauses
sampling and resumes the same panel on restoration. Page updates use the existing
Live events, with no additional socket.

Trusted CLI/host code can use `runtime.activity/open`, `snapshot` and `close!`
for the same records. Keep the returned reader private. Capture cannot select a
foreign scope. A scope retains at most 64 active and 64 finished runs; the
per-environment registry allows sixteen scopes and sixteen reader leases each.
Capacity omits telemetry and counts omissions while actual tool work continues.
Dead callers appear interrupted and are swept on the next recorded operation;
their sampled elapsed time is an upper bound. No source bodies, result values,
raw errors, cache keys, PIDs or execution handles enter the public records.

`live.inspector/attach` supports app construction directly. `:assets-root` can
supply an app-owned pair of `inspector.js`/`inspector.css` files, each at most
64 KiB. Otherwise the exact SDK assets are used. Close a directly attached
app with `live.inspector/close!` when its owning surface is retired.

See `examples/tooling/work-observatory.bl` for real Editor/Check/Index actions.
The focused qualification inventory is `scripts/projection-preflight.json`.
`research/work-observatory/scenarios/inspector.bl` runs real native input and
screenshots through `scenario`, `browser.page` and `browser.film`. Browser
verdicts are witnessed, never represented as model proofs.

Cold indexing and checks initialize their lazy providers before capturing memo
identity. The first index performs one computation; the second identical index
and check perform zero new compiler computations. The first file in the focused
qualification inventory enforces this transition in a fresh VM.

With an owned preview on 4057, replay the browser acceptance in one capped VM:

```sh
scripts/inspector-scenario --sdk /nix/store/QUALIFIED-SDK \
  --url http://127.0.0.1:4057 --out .local/inspector-browser-evidence
```

The runner requires the local optional browser helper/runtime. It retains native
screenshots, twenty-three witnessed claims, source/helper hashes and the exact SDK
pin, and rejects changed test inputs. It never produces an SDK or starts an app.

Cold-start assertions are authoritative in canonical SDK qualification. Private
source preflight compiles candidates first and can warm providers that an SDK
loads lazily. Keep the canonical first-to-second-call gate ahead of the rest of
the tests; do not substitute a warmed source overlay for this release check.

CI also declares `test/bl/data/tool_cold_start_test.bl` in
`scripts/test-isolation.json`, so sharding cannot warm its providers in another
test first. Both full and call-only indexing must retain their first answer.
