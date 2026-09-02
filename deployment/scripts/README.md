# Deployment Scripts

`customer-instance.sh` is the operator-controlled Mission 21 foundation for
isolated customer and ephemeral test instances. It consumes
`deployment/customer/modules.txt` and approved release bundles. It never
targets the canonical DEV or Demo databases and never stores runtime state in
the repository.

The existing `odoo-dev.sh` and `odoo-demo.sh` scripts remain environment-
specific. Do not use Demo seed, Demo license, Demo credentials, or Demo
database volumes for customer provisioning.

Runtime image selection is controlled by
`deployment/runtime/runtime-lock.json`. Use `runtime-images` to display the
approved references and `runtime-verify` for an offline local check.
`runtime-fetch` is the only explicit image acquisition command. Normal
customer lifecycle commands fail closed when a locked image is unavailable;
they do not pull mutable tags.

Customer recovery points are created with `customer-instance.sh backup` using
the pinned external age tool and a public recipient file. The command writes
an encrypted archive, an immutable manifest with component checksums, and a
checksum sidecar. Snapshots are recorded inside a maintenance/write-stop
window, with the prior Odoo service state restored on both success and
failure. `retention` defaults to dry-run and only operates inside an instance's
marked external recovery repository. `restore-validate` requires a separate
private age identity, validates all checksums before extraction, remaps the
filestore to the disposable target database, and only allows disposable test
instances. Keys, archives, restored data, and off-host destinations remain
outside Git.

## Recurring customer backups

`customer-backup-scheduler.sh` validates and installs the M29.2 per-instance
systemd templates. Configuration is root-owned and external to the repository.
The scheduler delegates encrypted backup, verification, off-host transfer, and
retention to the existing `customer-instance.sh` and M29.1 tooling.

```bash
./deployment/scripts/customer-backup-scheduler.sh validate-config --config /etc/perfect-match/customer-backup/<instance>.json
./deployment/scripts/customer-backup-scheduler.sh install <instance> --config /etc/perfect-match/customer-backup/<instance>.json
./deployment/scripts/customer-backup-scheduler.sh status --config /etc/perfect-match/customer-backup/<instance>.json
./deployment/scripts/customer-backup-scheduler.sh health --config /etc/perfect-match/customer-backup/<instance>.json
```

The fixed UTC intraday cadence is every four hours with no more than 30
minutes of timer jitter. Daily and monthly timers are separate retention
tiers. A shared nonblocking lock prevents overlapping runs for one instance
while different instances remain independent. Status files contain only
non-secret operational fields and are written atomically. Health exit codes are
0 healthy, 1 stale/failed recovery point, and 2 invalid infrastructure.
Production installation is not part of M29.2; the disposable rehearsal uses
an accelerated test-only driver.
