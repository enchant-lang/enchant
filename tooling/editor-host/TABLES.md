# Structured packages

The standard package includes typed `table`, `table-row` and `table-cell` blocks.
A table owns the `rows` slot; each row owns `cells`. Cells contain editable text
and inline functions. The package plans semantic reducer operations and keeps
row/column edits in the same journal and undo system as other document edits.
Source codecs must validate and serialize this structure explicitly.

Custom commands receive the stable command `:seed` in their context, suitable
for naming a new subtree. A plan can return `:selection` without `:ops`; that
moves the caret without creating a proposal or content revision.

`:menu "insert"` includes a custom command in the insertion menu while retaining
its custom planner. A custom `:shortcut` such as `"Tab"` or `"Shift-Tab"` takes
precedence when its `:when` predicate enables it. `:input-type` can bind a native
beforeinput intent such as `"insertParagraph"`; the same command receives the
input text as `:text`. Composition and read-only admission remain host-owned.

Packages can provide `:editor/command-policy`, a pure function of context and
catalogue item. It can restrict `:enabled` and supply a refusal `:reason`; it
cannot enable an otherwise unavailable command or change its semantic identity.
Tables use this to keep generic turn/indent/delete actions from splitting their
structure. Direct source writers must independently validate proposed structure.

Pure projections can emit buttons with `data-edit-command` and
`data-edit-command-target`. The host bookmarks that typed block and invokes the
shared planner; no package DOM handler is needed. Authoring-only groups carry
`data-edit-controls`, which immutable rich readers remove as a whole.

Table keyboard behavior follows Org's next-field/next-row conventions. Escape
moves after the table. Cell boundary deletion navigates rather than merging the
row/cell structure. Rectangular clipboard operations and cross-cell input still
require separate qualification; this initial package does not claim those paths.

Native source conventions are documented in the [Org table editor manual](https://orgmode.org/manual/Built_002din-Table-Editor.html) and [column alignment manual](https://orgmode.org/manual/Column-Width-and-Alignment.html). In particular, a literal vertical bar is written with `\vert` (or `\vert{}` within a word); backslash-pipe is not the documented escape. Native alignment uses `<l>`, `<c>` and `<r>` cookies.

Clipboard work (qualification pending): packages can provide
`:editor/clipboard` handlers for `:selection`, `:copy`, `:cut` and `:paste`.
The persistent session owns hooks and executes returned plans through the normal
journal. The native host only reads/writes trusted clipboard formats. Table
cross-cell endpoints define a highlighted rectangle; cut clears its cells and
keeps the table. Paste can grow bounded rows/columns and restores inline ranges
with fresh application IDs. TSV quotes preserve tabs/newlines; HTML uses real
table/row/cell elements and refuses merged/nested tables. Unsupported cell
structures refuse before a proposal. A large grid is limited by the reducer's
4096-operation batch budget; paste a smaller section when needed.

Selection range providers
-------------------------
Packages may supply `:editor/selection-ranges`, a pure function of the command
context. Return nil to defer, `{:ranges [{:block id :from cp :to cp}]}` to supply
semantic text ranges, or `{:reason "…"}` to refuse an unsupported selection.
Ranges reference current blocks and use Unicode code-point offsets. Commands
validate them, omit empty spans, and cap formatting at 4096 operations. The same
ranges drive inline coverage, formatting and text transforms; command policies
receive `:selection/ranges` and `:selection/reason`.

The standard table provider uses the clipboard rectangle: selections across
cells format complete cells inside the rectangle, including reversed selections.
Unselected cells between those cells in document order remain untouched. A
selection crossing table/prose or separate tables is refused before proposing
an edit. Select the table itself for whole-block structural actions.
