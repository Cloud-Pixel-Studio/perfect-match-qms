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
checksum sidecar. `retention` defaults to dry-run and only operates inside an
instance's external backup directory. `restore-validate` requires a separate
private age identity, validates all checksums before extraction, and only
allows disposable test instances. Keys, archives, restored data, and off-host
destinations remain outside Git.
