# ADR-071: CAPA Root Cause Methodology Integrity

## Status

Accepted for implementation in `pm_qms_capa`.

## Decision

CAPA retains the common `pm.qms.capa` record and `pm.qms.capa.why` model, and
adds dedicated Fishbone and Is / Is Not child models. The selected method is
chosen in draft and locks when analysis starts. Each method has a controlled
workflow gate before actions can be planned, and all methods share a summary
and verified root cause.

5 Why uses five fixed, idempotently initialized slots. Is / Is Not uses exactly
the What, Where, When, and Extent dimensions. Fishbone accepts multiple causes
per category and requires evidence and rationale for a confirmed cause. Other
requires a named method/tool plus the common summary and verified root cause.

## Consequences

- ORM validation is authoritative; this release does not add SQL unique constraints.
- Fixed child structures cannot be added, removed, or structurally edited by customers.
- RCA detail is immutable after implementation starts; an ineffective CAPA may
  reopen for action planning while its method remains locked.
- Existing legacy 5 Why duplicates remain readable and are not auto-cleaned.
- Demo seed identity is `(capa_id, sequence)` so changing answers or dates cannot
  create new 5 Why rows.
- Standard requirement text and other standards are outside this change.

## Rejected Alternatives

- A generic untyped RCA child model would make method-specific validation and
  customer UX ambiguous.
- A database uniqueness constraint was deferred until legacy duplicates are
  separately assessed and cleaned through an authorized migration.
