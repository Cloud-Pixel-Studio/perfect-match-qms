# ISO 9001:2026 controlled migration execution record

## Purpose

The execution record provides an auditable workflow for a separately operated
ISO 9001 edition migration. It records authorization, evidence, counts, outcome,
rollback, and independent closeout. It does not connect to a customer database,
run migration commands, import records, deploy software, or claim conformity or
certification.

The generic QMS remains standard-neutral. This workflow belongs only to the
ISO 9001 add-on and preserves historical ISO 9001:2015 records.

## Entry gate

An execution record can be prepared only from an approved controlled migration
package. The record snapshots the package manifest SHA-256 and verifies the
approved package integrity at preflight, start, and closeout.

Only one execution record is permitted per approved package.

## Required separation

- the operator and independent reviewer must be different authorized users;
- both must be QMS Managers or Administrators with access to the company;
- only the reviewer authorizes execution and closes the record;
- only the operator records start, outcome, and submits closeout.

Technical administration alone does not grant business authorization.

## Lifecycle

1. **Draft** — document the non-secret target reference, fresh preflight,
   backup accessibility, restoration rehearsal, isolated dry run, and explicit
   authorization basis.
2. **Preflight Passed** — freeze a deterministic control snapshot and SHA-256.
3. **Authorized** — the independent reviewer authorizes the unchanged controls.
4. **In Progress** — the assigned operator records that the separately operated
   activity started. No migration command is executed by PMQMS.
5. **Outcome Recorded** — record immutable-log reference, post-migration checks,
   created/reused/skipped/rejected/manual-review counts, and rollback decision.
6. **Submitted for Closeout** — the operator submits evidence.
7. **Returned** — the reviewer returns incomplete evidence.
8. **Closed** — the reviewer independently accepts the outcome and the record
   becomes immutable.

Outcomes are **Completed**, **Failed**, or **Rolled Back**. Rolled-back outcomes
require an executed rollback decision and evidence.

## Evidence rules

References must be non-secret. Do not embed credentials, private keys, database
dumps, licensed ISO publication text, or raw backup content. Evidence and logs
remain in approved controlled repositories.

Counts distinguish:

- records created;
- historical records reused;
- records skipped;
- records rejected;
- records requiring manual review.

These counts support reconciliation; they are not a certification statement.

## Explicit non-capabilities

There is intentionally no `action_execute`, `action_migrate`, database
connection, deployment operation, or automatic rollback. This increment creates
the governed execution record only. Operating a migration remains a separate,
explicitly authorized runbook activity outside the product workflow.

No Demo2, customer VM, customer database, license, historical evidence, or
completed ISO 9001:2015 record is modified by this feature.
