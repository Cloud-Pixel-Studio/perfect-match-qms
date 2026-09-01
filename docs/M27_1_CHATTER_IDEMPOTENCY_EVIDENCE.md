# M27.1 Chatter Idempotency Evidence

## Scope

This document records sanitized evidence for the corrective work associated
with Issue #88, Issue #90, and the operational follow-up Issue #92. It describes the observed behavior without
including message bodies, addresses, user names, customer values, database
identifiers, or other source-system content.

The canonical Demo was not modified during this investigation.

## Live read-only observation

The supplied Demo backup was verified before use:

- Archive SHA-256: `19dda54fe7a32379d648c1e05bbbab0c3a35d73eb9a051fad0757e0d500ab03c`
- Observed second-update window: one minute at the recorded deployment time
- New `mail.message` rows: 58
- Affected modeled records: 43 snapshot inputs and 7 QMS people
- Messages without a model: 8
- Rows with tracking values: 0 of 58

The modeled distribution was 43 messages for management-review snapshot input
records and 7 for QMS people. The eight unmodeled rows were outgoing mail
queue records in exception state, without a business model or record link.
They had zero tracking values, were not reproduced by the final corrected
isolated seed cycle, and show no evidence that they were QMS record chatter.
They are classified and tracked in Issue
[#92](https://github.com/Cloud-Pixel-Studio/perfect-match-qms/issues/92) as a
P2 operational/email follow-up. They are not resolved or silently ignored;
no message deletion or rewriting is authorized.

No message body, author identity, recipient, customer identifier, or raw
source value is retained in this evidence.

## Disposable reproduction

The verified backup was restored to an isolated PostgreSQL container and used
only for diagnosis. The live Demo PostgreSQL service was not used for writes.

The effective update operation was:

```text
odoo -d pmqms_demo --init pm_qms_app,pm_qms_license --update pm_qms_app,pm_qms_license --stop-after-init
```

followed by the repository's `deployment/demo/seed_demo.py` through an
isolated Odoo shell. The seed database guard remained in force.

Baseline counts included 2,445 `mail.message` rows and 41 management-review
snapshot inputs. The first isolated update produced 72 new messages, 43 of
which were snapshot-input messages and 7 of which were QMS-person messages;
the remaining first-cycle messages were normal fixture setup activity. The
second identical update produced 50 new messages: 43 snapshot-input messages
and 7 QMS-person messages. It produced no new tracking values and no new
business records. The eight unmodeled outgoing rows observed in the live
window did not occur in this reproduction.

The final corrective branch was then installed in a fresh disposable database,
with the externally issued test license imported through the supported shell
procedure. The first corrected seed produced the fictional fixture with stable
counts, including 260 `mail.message`, 13 `mail.tracking.value`, 0
`mail.activity`, 23 `mail.followers`, 57 `ir.attachment`, 4 training records,
and 4 qualification records. The second identical corrected seed exited 0 and
left every listed count unchanged. No unmodeled outgoing password-change
messages were created by the corrected cycle. The existing CAPA Why warning
remained an expected fixture warning and did not affect the command exit
status.

## Root cause

1. `action_generate_snapshot` deleted every system-generated snapshot input
   and recreated it. The records therefore received new creation messages on
   every seed run.
2. The Demo `upsert` helper always wrote the payload to an existing record,
   including unchanged QMS-person values. Tracked fields therefore emitted
   messages even when the logical value was unchanged.
3. The seed rewrote managed passwords for existing technical and QMS persona
   accounts. Odoo treated those writes as password changes and queued outgoing
   security messages on repeat runs.

## Corrective design

- Snapshot inputs now use review/category/source-type/source-identifier
  identity and are synchronized in place.
- Unchanged snapshot values do not call `write()`.
- Changed or newly created system snapshot values use the narrow
  `tracking_disable` context for the synchronization operation only.
- Stale generated inputs are deactivated rather than deleted, preserving
  history.
- Snapshot event/date updates occur only when the synchronized content changes.
- The generic Demo `upsert` helper compares scalar, relational, and command-set
  values before writing.
- Managed passwords are applied only when a Demo account is created; existing
  account passwords are not rewritten by a repeat seed.
- Normal user edits and normal tracked QMS changes remain on the standard Mail
  tracking path.

The implementation does not globally disable tracking, remove tracking from
models, delete existing messages, or change customer data.

## Regression coverage

- Addon integration coverage runs two snapshot generations and asserts stable
  input IDs, stable values, and unchanged counts for messages, tracking,
  activities, followers, and attachments.
- The addon history suite continues to assert that a normal user change creates
  a tracked message; the idempotency test also exercises a normal user write
  after the system synchronization path.
- Demo seed tests assert that generic no-op upserts do not call `write()`.
- Demo seed tests execute Odoo many2many command semantics in order and assert
  that an already-satisfied link is not written while a missing link is.
- Demo seed tests assert that existing technical and QMS persona passwords are
  not rewritten during repeat seeding.
- The isolated reproduction was executed against a disposable database with
  the documented Odoo module update command and the repository seed script.
