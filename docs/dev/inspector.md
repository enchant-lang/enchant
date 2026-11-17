# Development inspector

Enable the SDK dock when serving a development app:

```clojure
(app/serve application
  {:port 4040
   :devtools {:enabled? true :authorize developer?
              :work {:imports imports-owner}
              :projections {:totals totals-reader}}})
```

`developer?` receives the app's resolved principal and must return exactly true.
The default is off. Unauthorized viewers receive the original screen; assets
and snapshots return 404. Existing HTTP handlers still compose. `app/stop!`
releases the listener, internal shared connection and inspector reader.

The injected dock shows page updates, Loom spacing/colours/corners, real tool
activity and registered owner status. Click an update to inspect its server
render. Click a tool run to see actual cache computations, reuse decisions,
admission waiting and child runs. Function labels come from actual analysis
worklist evaluations, with sixteen labels retained. They are not a complete
function list. Check always runs house rules, including when compiler facts
are reused. Browser update counts count patch operations, not CPU usage.

Activity records instrument `lsp/analyzed`, `bl.check/analyze-source` and
`codebase/index-source`. They stay in the caller's environment and VM scope.
They describe work in this scope; a separate cold CLI VM is a separate runtime.
No observer starts an editor request, check, index, projection subscription or
worker. A hidden/closed dock has no polling; an open Tools/Server panel allows
one request at a time with an abort deadline. Page updates use the existing
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
