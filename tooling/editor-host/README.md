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

Pure block renderers also receive `context.siblings`: the current same-parent
sequence from the document tree. It reflects structural moves and lets packages
render ordered sequences and source-owned counters without inspecting DOM order
or storing a second document. The existing `node` two-argument call remains
valid; its renderer context has no sibling sequence unless supplied.

Package block renderers receive `:siblings` in their context in both the initial
view and incremental node shells. A renderer whose shell depends on sibling
content/order declares `:render-context #{:siblings}` in its block specification.
The host then expands sibling patches, including both scopes of a structural
move, and compares rendered shells before reusing unchanged block data. Ordinary
renderers retain their narrow patch set.

A package can provide `:editor/sibling-context`, a pure function receiving
`{:siblings [...]}` and earlier derived context, returning a map of extra context
fields. Use namespaced keys. It runs once per sibling scope for each projection,
so packages can derive numbering or other sequence data in linear time instead
of rescanning the sequence for every block. Renderers also receive the normal
`:text` and `:slots` values. Keep source parsing, application grants and IO out
of these callbacks. `live.edit.projection/project` and `targets` expose the same
pure projection/invalidation contract for native tests and host integration.

A block may declare a pure `:text-range` callback receiving `[block context]`.
Return `{:from cp-start :to cp-end :isolated true :label "Field name"}` to expose
only a field within its complete model text. Bounds are Unicode codepoints;
invalid or reversed ranges refuse projection. Inline mark identities and ranges
keep their original model coordinates. Empty fields retain a caret placeholder.
The host maps DOM selections and native input back to absolute model offsets,
including composition and repeated text. `data-edit-start` and `data-edit-tail`
describe the envelope; the tail length stays stable as a field grows, avoiding
shell replacement on every keystroke. Ordinary blocks keep full-text behavior.

Use an isolated field inside a noneditable package shell when adjacent metadata
must stay outside native text input. The host applies current read-only/conflict
state to isolated fields, and the reader removes their editability and hooks.
This is a projection/input primitive, not field validation or publication
authority. Packages must supply appropriate Enter/structural commands before
enabling it for a source grammar; the default split still operates on the full
model text. Application writers continue validating the complete candidate.

An application may return a correctable validation refusal only after durably
retiring the exact refused proposal. The reply carries `:correctable true`, its
`:id`, original `:basis` and `:digest`, and a bounded human `:reason`. The replica
accepts it only for the exact sent head at the current confirmed revision. It
retains the candidate and permits local correction/undo while withholding that
proposal from publication. A correction combines the private operations into a
bounded atomic batch with a fresh identity and the same confirmed basis. Typing
already queued before the refusal is combined by the session without requiring
another keystroke. Delayed old refusals cannot invalidate the newer proposal.

Authoring stays available during validation, with a visible explanation and
Needs correction status; publication barriers reject promptly. Recovery retains
the refusal, original pending proposals and retired identities. New confirmed
source while validation is unresolved becomes a review conflict. The generic
host does not classify application failures as correctable, retire proposals on
the server, or authorize retries. Applications must preserve negative receipts
and recheck current grants in their ordinary final writer. Permission, identity,
ownership and protocol failures remain recovery conflicts.
