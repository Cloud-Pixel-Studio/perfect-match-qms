# DEV Backup And Recovery

Mission 04 adds a DEV backup quality gate for the Odoo development stack.

This procedure covers:

- PostgreSQL database dump.
- Odoo filestore archive.
- DEV Odoo configuration needed for restoration.

Backups are written outside Git under
`/opt/perfect-match/backups/odoo-dev` by default. That directory is intended to
be permission-restricted because DEV configuration files can contain secrets.

## Create A Backup

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/backup-dev.sh backup
```

The script creates:

- `pmqms-dev-<timestamp>.tar.gz`
- `pmqms-dev-<timestamp>.tar.gz.sha256`

It validates the archive by checking the PostgreSQL dump catalog and filestore
archive.

## Validate An Existing Backup

```bash
./deployment/scripts/backup-dev.sh validate /opt/perfect-match/backups/odoo-dev/pmqms-dev-YYYYMMDDTHHMMSSZ.tar.gz
```

## Restore To A Disposable Database

Use a disposable target for restore rehearsals:

```bash
./deployment/scripts/restore-dev.sh \
  --backup /opt/perfect-match/backups/odoo-dev/pmqms-dev-YYYYMMDDTHHMMSSZ.tar.gz \
  --target-db pmqms_restore_validation \
  --confirm-target-db pmqms_restore_validation \
  --drop-after-restore
```

The restore script refuses to overwrite existing databases unless
`--replace-existing` is provided with the matching confirmation. Restoring over
`pmqms_dev` is refused unless `PMQMS_ALLOW_ACTIVE_DEV_RESTORE=I_UNDERSTAND` is
set explicitly.

## Recovery Notes

The backup archive includes DEV configuration to support restoration. Do not
commit backup archives, extracted backups, database dumps, filestore archives,
or generated configuration into Git.

Production backup, retention, encryption, offsite storage, and monitoring are
future work. This Mission 04 gate is a DEV validation foundation.
