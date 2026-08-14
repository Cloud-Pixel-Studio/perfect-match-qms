# Backup Strategy

This directory will hold backup automation artifacts. The existing Plane deployment is treated as production infrastructure, so backup implementation must be non-destructive and reversible.

## Current Plane Assets To Protect

- Plane PostgreSQL data volume.
- Plane uploaded files and object storage volumes.
- Plane Redis and RabbitMQ volumes where operational recovery requires them.
- `/opt/plane-selfhost/plane-app/` Compose configuration.
- Plane environment files, backed up separately with restricted permissions because they contain secrets.
- Reverse-proxy configuration and TLS renewal automation on the Nginx proxy VM.

## Minimum Backup Design

1. Run a nightly logical PostgreSQL backup from the Plane database container.
2. Archive uploaded files/object-storage data and critical Docker volumes nightly.
3. Store Compose and environment configuration in a protected, encrypted backup target.
4. Keep local short retention plus an off-host copy.
5. Monitor backup freshness and failed jobs.
6. Perform periodic non-destructive restore rehearsals into an isolated VM or staging environment.

## Safety Rules

- Do not run destructive restore tests against the live Plane instance.
- Do not commit credentials, database dumps, TLS private keys, or environment files.
- Do not delete Docker volumes or containers during backup validation.
