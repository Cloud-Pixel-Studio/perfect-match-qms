# Customer Backup and Restore Runbook

## Backup

Before an upgrade or other destructive maintenance:

```bash
PMQMS_BACKUP_RECIPIENT_FILE=/secure/backup/recipient.age \
./deployment/scripts/customer-instance.sh backup northstar-precision \
  --class daily \
  --off-host-dir /secure/off-host/northstar-precision
```

The archive is written under the instance's external `backups/` directory as a
`.tar.age` file and contains the PostgreSQL custom dump, Odoo filestore
archive, environment ID, runtime lock, active license reference, and
non-secret manifest. The encrypted archive has a sibling `.manifest.json` and
`.sha256` file. The manifest records per-component SHA-256 values, release
identity, source identity, UTC time, and recovery-point class.

The recipient file is an operator-managed public age recipient. The matching
private identity is supplied separately for restore and is never copied into
the archive, logs, repository, or generated evidence. M29.1 requires the
operator to use the pinned age version recorded by `PMQMS_AGE_VERSION` (the
default is `1.2.1`) and fails closed when the tool, recipient, or any required
component is missing. The database and filestore are collected during the
same controlled maintenance/write-stop window; this procedure does not claim
online consistency.

## Retention

Preview retention decisions before deletion:

```bash
./deployment/scripts/customer-instance.sh retention northstar-precision \
  --now 2026-09-01T00:00:00Z
```

Apply only after reviewing the JSON decisions:

```bash
./deployment/scripts/customer-instance.sh retention northstar-precision \
  --now 2026-09-01T00:00:00Z --apply
```

The policy keeps intraday points for 7 days, daily points for 30 days, and
monthly points for 12 months. Invalid or incomplete archives are never
eligible for deletion, and the newest valid recovery point is always kept.
Deletion is restricted to the instance's external `backups/` directory.
Passwords and private signing keys are never placed in the archive.

Retention is operator-configured outside Git. Do not delete the only known
recovery point. Copy archives to encrypted, access-controlled off-host storage
according to the customer's retention policy.

## Same-instance recovery

Restore requires a controlled maintenance window, a verified archive checksum,
the same environment identity, the matching license, and a healthy target
runtime. Restore the database and filestore using the target instance's
operator procedure, then verify license status, health, organization, users,
sites, and application logs. This preserves the customer's identity.

## Validation

Mission 21's ephemeral test uses:

```bash
PMQMS_BACKUP_IDENTITY_FILE=/secure/backup/identity.age \
./deployment/scripts/customer-instance.sh restore-validate \
  pmqms-customer-e2e-test \
  /opt/perfect-match/instances/pmqms-customer-e2e-test/backups/<archive>.tar.age
```

The command requires a `test` source, validates the outer checksum and
manifest, decrypts with the separately supplied identity, verifies every
component before restoration, restores into an explicit recovery instance
with the archived identity/license, checks health and license state, and
removes only the recovery instance. The measured elapsed time is evidence for
that disposable rehearsal only; it does not establish the proposed eight-hour
RTO by design alone.

## Recovery versus cloning

Recovering the same customer preserves its identity and license. A new
customer always receives a new slug, database, filestore, secrets, environment
identity, activation request, and license. Copying a customer directory as a
normal provisioning method is forbidden.

## Recurring scheduler

M29.2 provides templated systemd services and timers per customer instance.
Production intraday slots are fixed UTC at 00:00, 04:00, 08:00, 12:00, 16:00,
and 20:00, with `Persistent=true` and at most a 30-minute randomized delay.
The designed maximum interval is 4.5 hours, below the six-hour RPO target.
Daily and monthly points run at 00:45 UTC daily and 01:30 UTC on the first
calendar day, respectively. Retention is 7 days for intraday, 30 days for
daily, and 12 calendar months for monthly points.

Use one root-owned configuration file per instance outside Git. It contains
paths and policy only; no private age identity or credential is stored there:

```json
{
  "instance_slug": "northstar-precision",
  "instance_root": "/opt/perfect-match/instances/northstar-precision",
  "recipient_file": "/etc/perfect-match/backup/recipient.age",
  "local_staging_repository": "/opt/perfect-match/instances/northstar-precision/backups",
  "off_host_destination": "/opt/perfect-match/off-host/northstar-precision",
  "status_path": "/var/lib/perfect-match/backup-status/northstar-precision.json",
  "monitoring_status_destination": "/var/lib/perfect-match/backup-status/northstar-precision-monitoring.json",
  "timeout_seconds": 1800,
  "backup_cadence_minutes": 240,
  "max_jitter_seconds": 1800,
  "retention": {"intraday_days": 7, "daily_days": 30, "monthly_months": 12}
}
```

`health` returns 0 while the latest verified point is no older than six hours,
1 when stale, and 2 for missing or invalid state/configuration. A failed
backup writes sanitized failure status, preserves the previous successful
point, releases the lock, and does not run retention. External alert delivery
is not configured by this repository. Production scheduler installation is
**NOT EXECUTED** by M29.2, so recurring production RPO remains unproven until
an authorized customer deployment and operational observation.
