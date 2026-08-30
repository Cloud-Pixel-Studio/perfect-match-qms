# Backup Strategy

This directory holds planning notes for non-destructive, reversible backup
automation for Perfect Match QMS environments. Customer databases, filestores,
secrets, and evidence remain operational data and are never committed here.

The former Plane deployment is retired. Any historical Plane backup references
are retained only as context and are not supported runbook instructions.

## Minimum Backup Design

1. Run a scheduled logical PostgreSQL backup for each approved QMS environment.
2. Archive each environment's filestore and critical Docker volumes nightly.
3. Store Compose and environment configuration in a protected, encrypted backup target.
4. Keep local short retention plus an off-host copy.
5. Monitor backup freshness and failed jobs.
6. Perform periodic non-destructive restore rehearsals into an isolated VM or staging environment.

## Safety Rules

- Do not run destructive restore tests against a live environment.
- Do not commit credentials, database dumps, TLS private keys, or environment files.
- Do not delete Docker volumes or containers during backup validation.
