# Refuse an excessive declared width before calculating its forecast

The qualified standalone word prototype currently computes its forecast before
selecting the first exceeded limit. Its billion-bit declaration test uses a
small integer width and does not construct that word, but an already-present
very large width integer would still participate in unnecessary metadata
multiplication before the width refusal.

Move the declared-width limit decision ahead of forecast arithmetic after the
operation's shape and sort relationships are validated. Keep malformed requests
separate from resource-incomplete ones. An over-width result should explicitly
report that forecast arithmetic was not run; later intermediate/work refusals
can retain their prospective forecast. Check a large existing width integer,
exact width boundaries and unchanged valid-operation results. The coordinate
prototype already checks width before its charged right shift.

This project refinement is qualified in prototype v2 by 3,526 focused assertions. The selected SDK does not import these
prototypes and its managed policy remains numeric. The fixed constructor width
ceiling and the new managed admission rules remain separate gates; a resource
override must not enlarge the term grammar. No runtime-cost theorem is claimed.
