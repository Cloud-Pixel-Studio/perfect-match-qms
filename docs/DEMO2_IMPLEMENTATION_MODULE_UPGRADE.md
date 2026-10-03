# Demo2 targeted implementation-module upgrade

The `upgrade-implementation-module-demo2` launcher command is an operational
path for updating only `pm_qms_implementation` in the isolated Demo2 database.
It is not the general Demo `update`, `install`, seed, reset, or licensing path.

## Preconditions and scope

The command rejects any instance/database/resource combination other than
`demo2` / `pmqms_demo2` / `pmqms-demo2`, the Demo2 volumes and network, and
ports 8171/8174. It also requires the existing locked runtime files, exactly
one already-running Odoo and PostgreSQL container in that Compose project,
healthy PostgreSQL, an installed module, and `ir_module_module.demo = false`.
It does not initialize or chmod secrets, start a stopped stack, provision a
license, initialize modules, or run any Demo seed. It stops only Demo2's Odoo
service, invokes the one-module update with `--stop-after-init`, then starts
that service only after a successful update. On failure Odoo remains stopped
for explicit recovery; the command does not retry or rollback automatically.

## What Odoo reloads

At the reviewed PR head, the implementation add-on manifest is version
`19.0.6.0.4` and has no pre-init/post-init hook or add-on migration directory.
The PR changes Python behavior only: an active/company domain on the wizard's
pack field and a model constraint rejecting any non-active pack. Neither
change adds a stored field or SQL schema constraint.

Odoo's `-u pm_qms_implementation` reloads the add-on's declared technical
data: security groups/rules, access-control CSV entries, two sequence
definitions, views, wizard view/action, and menus. Those external-ID-backed
technical records may be updated to the versioned definitions. The add-on's
demo-data XML is conditional on its installed `demo` flag; the command refuses
to run when that flag is true, preventing demo XML from being replayed. The
Demo2 database currently has the module installed with demo data disabled.

The update does not call the add-on's project generator and does not create
implementation projects, tasks, evidence, or seed records. Automated tests
verify the exact module argument, Demo2-only identity guard, the demo-data
precondition, stop/update/start ordering, failure behavior, and absence of
license-provisioning or Demo seed calls.

## Required operator sequence

1. Record the current Demo2 state and create/read-verify a complete database
   plus filestore backup.
2. Rehearse the same command on an isolated restore of that backup and compare
   pre-existing business rows and target module technical metadata.
3. Only after the rehearsal passes, run:

   ```bash
   PMQMS_DEMO_INSTANCE=demo2 ./deployment/scripts/odoo-demo.sh runtime-verify
   PMQMS_DEMO_INSTANCE=demo2 ./deployment/scripts/odoo-demo.sh upgrade-implementation-module-demo2
   ```

4. Verify module state, health, business-data preservation, and the UI picker
   using an authorized review account. Do not activate draft framework packs.
