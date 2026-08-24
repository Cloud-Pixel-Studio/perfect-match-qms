# Customer Backup and Restore Runbook

## Backup

Before an upgrade or other destructive maintenance:

```bash
./deployment/scripts/customer-instance.sh backup northstar-precision
```

The archive is written under the instance's external `backups/` directory and
contains the PostgreSQL custom dump, Odoo filestore archive, environment ID,
active license, and non-secret manifest. A sibling `.sha256` file is generated.
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
./deployment/scripts/customer-instance.sh restore-validate \
  pmqms-customer-e2e-test \
  /opt/perfect-match/instances/pmqms-customer-e2e-test/backups/<archive>.tar.gz
```

The command requires a `test` source, validates SHA-256, restores into an
explicit recovery instance with the archived identity/license, checks health
and license state, and removes only the recovery instance.

## Recovery versus cloning

Recovering the same customer preserves its identity and license. A new
customer always receives a new slug, database, filestore, secrets, environment
identity, activation request, and license. Copying a customer directory as a
normal provisioning method is forbidden.
