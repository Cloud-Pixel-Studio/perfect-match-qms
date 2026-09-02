# ADR-075: M29.1 Encrypted Backup, Restore and Retention

Date: 2026-09-01

## Status

Accepted for controlled disposable implementation; production and customer
execution remain separately authorized.

## Context

The existing customer backup path produced a plaintext tar archive containing
database and filestore material with only one archive checksum. That did not
prove that the database and filestore represented one recovery point, did not
provide per-component evidence, and did not define safe retention or an
authenticated off-host boundary.

## Decision

M29.1 uses `tools/backup/m29_backup.py` with the operator-pinned `age` tool
(default version `1.2.1`) to build an encrypted recovery-point archive. The
archive includes only the database dump, filestore archive, environment
identity, runtime lock, non-secret deployment manifest, and signed license
reference. A deterministic JSON manifest records source identity, release
identity, UTC time, recovery-point class, component sizes, and SHA-256 values.

The archive is encrypted with a public recipient supplied from an external
secret boundary. Restore requires the matching private identity from a
separate external secret boundary. Missing tools, keys, components,
manifests, checksums, unsafe paths, corrupted archives, and decryption errors
fail closed. Transfer copies the archive and both evidence sidecars to a
different operator-supplied directory and verifies the copied bytes.

Retention is an explicit dry-run first and applies only to a validated
instance backup directory. The policy is 7 days for intraday, 30 days for
daily, and 12 months for monthly points; invalid archives are retained for
review and the newest valid recovery point is never removed.

Restore validation creates only a new disposable test instance, verifies the
complete encrypted payload before database restore, checks health and license
state, and destroys the recovery instance. No Demo, production, customer,
Plane, RC11, or cloud-provider operation is part of M29.1.

## Consequences

The repository now has reviewable backup-format and failure-path evidence,
but it does not select a permanent off-host provider, establish production
monitoring, or demonstrate a production RPO/RTO. A later authorized rehearsal
must measure those values with fictional data and record the actual timings.
