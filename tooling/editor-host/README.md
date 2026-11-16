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
