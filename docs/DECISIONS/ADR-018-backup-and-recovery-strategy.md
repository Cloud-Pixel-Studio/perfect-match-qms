# ADR-018: Backup and Recovery Strategy

Date: 2026-08-14

## Status

Accepted

## Context

The DEV Odoo stack uses persistent Docker volumes. Before the product grows,
the repository needs a repeatable backup and restore validation procedure.

## Decision

Add `deployment/scripts/backup-dev.sh` and
`deployment/scripts/restore-dev.sh`.

Backups include a PostgreSQL custom-format dump, Odoo filestore archive, DEV
configuration, and a manifest. Restores require an explicit target database and
matching confirmation. Restoring over active `pmqms_dev` requires an explicit
environment override.

## Consequences

The DEV team can rehearse recovery safely using disposable databases. Production
backup automation, encryption, retention, offsite storage, and monitoring
remain future work.
