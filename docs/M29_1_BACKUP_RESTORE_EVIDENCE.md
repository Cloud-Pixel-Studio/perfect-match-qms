# M29.1 Backup, Restore and DR Evidence

## Scope

M29.1 implements an encrypted recovery-point format and disposable restore
validation. It does not operate Demo or production/customer environments.

## Recovery-point format

`tools/backup/m29_backup.py pack` creates a pinned-age encrypted `.tar.age`
archive plus `.manifest.json` and `.sha256` sidecars. Required payloads are:

- PostgreSQL custom dump;
- customer filestore archive;
- environment identity;
- runtime lock;
- non-secret deployment manifest;
- signed active license reference when present.

The manifest is versioned and records source instance/database identity,
release SHA, UTC creation time, recovery-point class, and a sorted per-file
SHA-256/size list. Secrets and private identities are rejected from the
payload by construction and remain outside the output directory.

## Supported operations

- `pack`: collect and encrypt one consistent maintenance-window recovery point;
- `verify`: validate sidecar checksum and outer manifest;
- `unpack`: decrypt and verify every payload checksum before extraction;
- `transfer`: copy archive and sidecars to a distinct destination and verify;
- `retention`: produce a JSON dry-run or apply validated retention decisions.

The customer wrapper exposes `backup`, `restore-validate`, and `retention`.
Retention defaults to dry-run, protects the newest valid point, preserves
monthly points within 12 months, and skips invalid/incomplete archives.

## Evidence boundary

The focused tests use fictional files and a local age-compatible test double;
they prove manifest, encryption invocation, checksum, transfer, retention,
calendar boundaries, atomic collision handling, and fail-closed behavior.
`tools/backup/test_m29_real_age.sh` downloads the official Linux amd64 age
1.2.1 release, verifies its published SHA-256, and proves pack, deep verify,
unpack, transfer idempotency, and retention with fictional data. Neither test
claims live Odoo performance evidence. A later authorized disposable Odoo
rehearsal must measure actual RPO/RTO, database/filestore preservation,
tenant isolation, cron/email behavior, and restore time.

The wrapper takes a maintenance/write-stop window: it records ordered quiesce,
database snapshot, filestore snapshot, and quiesce-end timestamps, stops and
restores the prior Odoo service state, and leaves PostgreSQL running only as
needed for the dump. The restore rehearsal is disposable and never targets
Demo, production, or customer data.
