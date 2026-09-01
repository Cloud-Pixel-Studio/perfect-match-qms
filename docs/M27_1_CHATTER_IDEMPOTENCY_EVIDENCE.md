# M27.1 Chatter Idempotency Evidence

## Scope

This document records sanitized evidence for the corrective work associated
with Issue #88 and Issue #90. It describes the observed behavior without
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
They were not reproduced by the isolated seed-update reproduction and are
therefore treated as a separate unreconciled mail-queue event, not silently
attributed to the seed correction.

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

After applying the corrective branch to a fresh restore of the same backup,
the first seed execution produced 22 messages from normal seed activity and
three newly required snapshot inputs. The second identical execution produced
zero new messages, tracking values, activities, followers, attachments, or
business records. The existing CAPA Why warning remained an expected fixture
warning and did not affect the command exit status.

## Root cause

1. `action_generate_snapshot` deleted every system-generated snapshot input
   and recreated it. The records therefore received new creation messages on
   every seed run.
2. The Demo `upsert` helper always wrote the payload to an existing record,
   including unchanged QMS-person values. Tracked fields therefore emitted
   messages even when the logical value was unchanged.

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
- The isolated reproduction was executed against a disposable database with
  the documented Odoo module update command and the repository seed script.
