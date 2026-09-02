# M29.2 Recurring Backup and RPO Evidence

## Scope

M29.2 adds repository tooling for recurring customer recovery points. It does
not install a scheduler on Demo, production, or a customer host, and it does
not change customer data. The production recurring RPO schedule is **NOT
PROVEN** by this repository change.

## Repository semantics

- Intraday: fixed UTC slots at 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00.
- Maximum jitter: 30 minutes.
- Designed maximum interval: 4.5 hours.
- RPO target: six hours.
- Daily tier: 00:45 UTC.
- Monthly tier: 01:30 UTC on the first calendar day.
- Retention: intraday 7 days, daily 30 days, monthly 12 calendar months.

The designed schedule semantics pass because the maximum interval is below the
RPO target. This is distinct from production deployment evidence.

## Disposable rehearsal

`tools/backup/test_m29_scheduler_rehearsal.sh` downloads the official age
1.2.1 release, verifies its pinned SHA-256, generates an ephemeral identity in
a temporary directory, and runs the actual M29.1 pack, deep verify, transfer,
and retention commands against fictional data. A test-only accelerated driver
invokes multiple scheduled slots, exercises a controlled failure, confirms
next-run recovery, checks off-host artifacts and status health, and cleans the
temporary workspace. It never uses production identities or instances.

The rehearsal is evidence for the scheduler contract and disposable execution
only. External alert delivery, recurring production observation, customer
policy approval, and an operational RPO are not claimed.

## Status contract

Status and monitoring JSON are atomic, mode `0600`, and contain only the
instance identifier, timestamps, archive identifier/checksum, verification,
duration, retention result, next run, sanitized failure code, failure count,
scheduler version, and optional release SHA. Health returns 0 when the latest
verified point is at or below six hours, 1 when stale, and 2 for invalid or
missing state/configuration.

## Reproduction

```bash
python -m unittest tools.backup.test_m29_scheduler
bash deployment/scripts/tests/test_customer_backup_scheduler.sh
bash tools/backup/test_m29_scheduler_rehearsal.sh
```

Generated archives, identities, status files, and reports remain in temporary
or operator-controlled locations and are not committed.
