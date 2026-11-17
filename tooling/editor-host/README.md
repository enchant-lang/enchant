# Native editor host build

`npm ci --ignore-scripts --no-audit --no-fund` followed by
`node tooling/editor-host/build-host.mjs` from the repository root rebuilds
the host asset and its input/artifact digests and third-party notices.
The lock is preserved from editable-projections commit
`a007273ca8d1dd009212d84cdc2acaf8d514f41a`, SHA-256
`62c4772968658211edb3dcbe9dddc604c2c33d25bc433e848fb1b9e5e465ea9f`.
No dependency upgrade was required for graduation. Package dev dependencies
are retained for provenance; this build uses esbuild and the runtime adapters.

Product packages can provide `:document-actions` through `live.edit.app/editor`.
Each data descriptor has label/icon and an ordinary href with optional download;
the product keeps its navigation and canonical export format. Absent this option,
the generic editor retains its default export/source actions.

`editor.geometry.hit({x,y})` returns a stable block ID and Unicode code-point
offset from actual input geometry, or null outside the canvas. Code inputs use
CodeMirror's coordinate mapping, prose uses native caret geometry. Consumers
must still validate the source/revision before offering an edit.

`live.edit.app/source-input` provides a source CodeMirror region through the same
bundle. The application supplies actor/document `:resource`, current `:confirmed`
text and `:confirmed-basis`, local `:value`/`:basis`, and a Live `:event` accepting
`:from :value` and `:from :basis`. Saving remains an explicit application command
with source admission checks. Recovery retains the original basis through reload
and remote edits; stale echoes never replace in-memory typing. The UI offers
exact text download and explicit discard, also when writing is no longer allowed.
`node --test tooling/editor-host/text-draft.test.mjs` checks recovery boundaries.

`:code-service` on `live.edit.app/editor` is an optional data descriptor with a
same-origin `:url`, language (default beam-lisp) and application `:context`.
The input POSTs `{operation,text,offset,context}` for completion, diagnostics and
hover. Offsets in requests/replies are Unicode code points. Replies use
`{from,options}`, `{diagnostics:[{from,to,message,severity}]}` or `{from,to,text}`.
The application owns authentication, source analysis and policy; the generic host
owns CodeMirror. Late answers are dropped after text changes and outstanding
requests abort on disposal. Failure keeps writing available. The already locked
CM autocomplete/lint versions are now explicit dependencies, with no upgrades.

Source inputs accept optional `:accepted {:value original-input :basis current}`
when an authoritative writer normalizes text. Exact draft value and current basis
must both match before the input adopts canonical bytes, preserving newer typing.

`live.edit.app/recovered-form` adds an effect-only recovery footer to an ordinary
Live element (a vector with attributes). Live retains native fields, input events,
focus and patch ownership. Descriptors declare flat keys, control IDs, server
changes paths and labels. Only attempted fields are cached; unrelated source
values never become edits. Original basis survives reload; removed fields remain
retained for download. `:event` assigns `:from :changes` and `:from :basis` into
application locals. Scope by actor/document/object. Optional accepted field values
acknowledge authoritative normalization. Storage failure leaves attempted values
in memory with a plain-text property draft download. No database write occurs
until the application's guarded save command.

For socket-local changes, provide `:locals {:changes path :basis path}` on a
recovered form. Recovery then uses ordinary leaf `:assign` terms, preserving the
same keyword-path semantics as native controls. Nested event payload maps remain
application data; the SDK does not change their keys or Live's wire contract.

Checkpoint-backed rich recovery retains unreadable pointer/checkpoint data for
explicit download; it never overwrites that record during normal mounting.
The host catches invalid cached replicas and keeps the current server snapshot
available. `DraftStore.remove()` clears an active editor's cache without stopping
future recovery. `discard()` also seals the retiring instance: late updates and
DOM disposal cannot recreate the pointer after a reload choice. Failed deletion
is reported before navigation. Checkpoint references stay inside their resource
scope. The storage tests exercise interruption, corruption, scope boundaries and
late disposal alongside the text/form/code-request checks.

Rich region drivers and the public editor expose `settle()`: flush code inputs
and wait for every pending authoring proposal to be confirmed. Offline, conflict,
composition, preview, read-only state, disposal and timeout reject with retained
writing. Live actions opt in using `data-live-await-region="<region id>"` on a
button or enclosing action form. The client waits, then reads the current action
term and its updated guards. Replaced targets, disabled actions and lost sockets
do not dispatch. This is a browser publication barrier; application writers must
still enforce current grants and exact source/editor guards. It never grants
publication authority or acknowledges an unsaved local proposal.

`data-live-await-regions` accepts a JSON array when publication depends on rich
writing and recovered fields. Drivers expose `ready()` as well as `settle()`;
Live rechecks all regions collectively and then confirms ordinary field events
through the ordered session mailbox before reading the latest action term.
The advertised `settlement` capability uses `settle`/`settled` frames, not a
dummy application command or database write. Disconnect, disposal and timeout
reject outstanding confirmations. Property and source recovery notify their
current values before waiting, including drafts restored at mount time.

Unreadable text/form caches expose their original scoped storage record for
download. Failed explicit deletion keeps attempted values in memory and can be
retried. Ordinary quota errors still permit durable publication of current
writing; unreadable drafts require an explicit recovery choice.

`live.edit.app/reader` renders an immutable typed document through the same
registry. It creates no region or authoring authority, strips Live handlers and
editing hooks, keeps accessible read-only task status and code fallback, and
accepts a pure `:icon` renderer with an optional `:label`. The caller still owns
current source/parent authorization and any bounded derived snapshot cache.

The code adapter adds its stable block ID as `context.block` to language-service
requests. Applications may pair that identity with their source basis to analyze
a working cell together with confirmed neighboring cells. The host does not
construct a second source reader or choose a namespace.
