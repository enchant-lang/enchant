# Reopen one saved answer by validating one selected payload

The isolated indexed-ledger prototype passed **129 assertions** on the selected
retained-request SDK. Its [actual receipt](evidence/indexed-ledger-prototype/qualification.json)
binds the source projection, twelve-record corpus, SDK and capped process.
The canonical SDK and `priv/lib` sources remain unchanged.

The projection applies the exact proposed `lookup`/`reopen` patch, plus explicit
namespace and require renaming. All existing payload normalization remains
byte-for-byte the same source. The test stores the actual twelve captured
fresh/supplied v2 and retained v3 request answers in an in-memory ledger.

Actual call-count tracing establishes twelve payload normalizations for one
complete scan and one for each selected lookup or reopening. Every selected
row equals its counterpart from that scan. Fresh point results preserve the
fixture's SAT, invalid-point and solver-claim distinctions. Missing IDs return
nil from lookup, wrong ID kinds refuse, and missing record reopening refuses.
A corrupt selected payload refuses. An unrelated corrupt payload leaves the
good selected row readable, while scanning the whole ledger still refuses.
Formal exchanges are counted and oracle methods denied; both counts stay zero.

The initial attempts are preserved. The fresh test first lacked loaded reserved
packet vocabulary, then diagnosed that refusal without interning names. It now
loads only its named protocol-profile modules before outer packet decoding;
unknown application names remain embedded graph data. Another run reached 118
passing assertions before its corruption fixture omitted Datom's required
`:db/id`; the corrected run targets the actual selected entity and passes all
controls. These refusals were not promoted into a successful qualification.

This is an in-memory project check, not a durable-reader performance benchmark,
production SDK qualification or historical native-execution authentication.
The next batch must apply the patch coherently, qualify actual durable reads in
fresh processes, preserve legacy formats and use one immutable SDK. A public
graph-packet reader should also own initialization of its closed schema vocabulary
so callers need not assemble those imports manually. The formal/total-language
goal remains active.
