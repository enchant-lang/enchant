# Native context ownership

This slice moves the portable context's authority from a caller's mutable atom
into the process that owns the native port. The client retains an ordinary
handle and optional diagnostic mirror. The owner retains the term registry,
generation, portable assumptions and a monotone context revision.

The starting cases exercise a lower-level native load, a caller forgetting an
assumption, corrupted local registry/generation fields and a handler restoring
its old mirror after changing the real context. These are API consistency
checks. They do not establish a security boundary against arbitrary Erlang
introspection or replacement of trusted runtime code.

## Common operations

| Operation | Owner responsibility |
| --- | --- |
| Context snapshot | Return the current portable assumptions, generation and revision to the borrower. Never return the port or private registry. |
| Portable load | Validate and export the original terms using the owned registry; commit portable assumptions only after the native load succeeds. |
| Portable scope | Build native IDs from the owned registry. Check the expected context revision in the same owner turn as the exchange. Scoped assertions remain temporary. |
| Portable reset | Reset from the owner's actual generation, clear the registry and assumptions and advance the revision. |
| Raw transport | Retain the compatibility escape hatch. A successful operation other than hello makes portable context accounting unavailable until a managed reset. |
| Failure | Preserve borrower checks, retirement, monitor cleanup and hard deadlines. Refusing a stale/opaque portable context must happen before a native check. |

The question layer obtains retained assumptions from an owner snapshot and
binds execution to that snapshot. Mutating a client mirror cannot erase an
assumption or restore an old owner revision. A managed reset can recover a
healthy context after a raw exchange; a failed native exchange still retires
the worker.

Intercepted logical sessions remain caller-owned BL data. Their fallback opens
a fresh native context for the complete captured question. Process handler
inheritance and executable code custody are a separate language/runtime slice.

Implementation and qualification are pending. Keep the selected immutable SDK
until its replacement passes focused qualification, then reuse that exact
artifact for regression and recorded dossier examples. Compiler authority
remains disabled.
