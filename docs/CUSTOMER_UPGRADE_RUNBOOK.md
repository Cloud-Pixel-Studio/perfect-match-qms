# Customer Upgrade Runbook

Customer environments run an explicit approved Perfect Match release bundle.
They do not pull main, feature branches, dirty worktrees, or arbitrary source
hashes.

## Preflight

Confirm the instance is a customer or disposable test environment, is
currently customer-ready, and has a consistent release/source/runtime
identity. The target must be a validated bundle whose product_version,
release tag, source commit, governed payload, checksums, and runtime lock
agree. A target must be a forward Git descendant of the current source and
must differ from the installed release.

Use:

~~~
customer-instance.sh upgrade <slug> \
  --bundle /secure/path/approved-target-bundle.tar.gz \
  [--to <bundle-product-version>] \
  [--approve-runtime-change]
~~~

The bundle is authoritative. Its modules.txt, customer Compose template, and
Odoo configuration template are copied into the instance at provisioning and
used for later upgrades. The operator checkout does not silently supply
release-specific execution assets.

## Controlled Upgrade

The command validates target images before mutation, rejects PostgreSQL major
changes, and requires --approve-runtime-change for an approved runtime-lock
change. It opens a maintenance window, creates the normal encrypted durable
backup with archive, checksum, and manifest, then creates a short-lived
permission-restricted local rollback snapshot. The snapshot contains the
database-independent runtime/addon and release-identity state needed for
immediate recovery and excludes instance secrets.

Target assets are staged before the current runtime is replaced. The command
stops Odoo, activates the staged release assets, renders configuration from
the target instance assets, and updates only the target release module list
with --without-demo=all --stop-after-init. It then starts the runtime and
checks HTTP health, license usability, first-user presence, release identity,
runtime identity, and customer-ready status.

Only after every gate passes is the deployment manifest marked deployed. The
durable encrypted backup remains subject to retention policy; the ephemeral
snapshot is removed after success.

## Automatic Rollback

Activation, module update, startup, health, license, identity, and
customer-ready failures trigger automatic rollback. The old database and
filestore are restored through the durable backup contract where needed, and
the local snapshot restores the old addons, release assets, runtime lock,
product/deployment manifests, and release identity. The old runtime is then
started and checked for customer readiness.

An upgrade failure always returns non-zero even when rollback succeeds:

~~~
UPGRADE_RESULT=FAILED
ROLLBACK_RESULT=PASS
~~~

If rollback fails, the runtime is left stopped where possible and the durable
backup reference plus the restricted rollback workspace are preserved for
operator recovery. The result is:

~~~
UPGRADE_RESULT=FAILED
ROLLBACK_RESULT=FAILED
~~~

Do not retry an interrupted upgrade state blindly. Resolve the preserved
recovery evidence first. Do not use the upgrade command to perform a
downgrade or to bypass authorization.
