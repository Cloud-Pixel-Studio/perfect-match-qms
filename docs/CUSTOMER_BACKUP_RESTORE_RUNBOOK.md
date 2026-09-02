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
