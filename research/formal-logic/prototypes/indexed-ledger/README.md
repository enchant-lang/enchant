# A selected ledger read should validate one payload

This is an unchecked project projection of the proposed indexed lookup patch.
The generator preserves all canonical payload normalization code and applies
only the exact proposed patch plus isolated namespace/require renaming. The
selected SDK and canonical `priv/lib` sources remain unchanged.

The focused check imports the actual twelve-record retained corpus, writes its
fresh and retained answers to an in-memory ledger, compares one complete scan
with selected reads and point reopenings, and counts actual payload normalizer
calls. It checks missing/wrong IDs and selected corruption. An unrelated corrupt
payload must leave the selected good row usable while a whole scan still refuses.
Formal exchanges and oracle methods are counted/denied. Durable fresh-process
readers and actual SDK qualification remain later gates.
