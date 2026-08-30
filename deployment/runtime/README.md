# Runtime Lock

`runtime-lock.json` is the source of truth for the approved Odoo,
PostgreSQL, and Alpine image references. Each reference includes its human-
readable tag and immutable content digest discovered from a validated
environment.

Use the environment-specific wrappers to inspect and prepare images:

```bash
./deployment/scripts/odoo-dev.sh runtime-images
./deployment/scripts/odoo-dev.sh runtime-verify
./deployment/scripts/odoo-dev.sh runtime-fetch

./deployment/scripts/odoo-demo.sh runtime-images
./deployment/scripts/odoo-demo.sh runtime-verify
./deployment/scripts/odoo-demo.sh runtime-fetch

./deployment/scripts/customer-instance.sh runtime-images
./deployment/scripts/customer-instance.sh runtime-verify <slug>
./deployment/scripts/customer-instance.sh runtime-fetch <slug>
```

`runtime-verify` is offline and only checks local Docker image metadata.
`runtime-fetch` is the explicit operator action that may contact a registry,
and it pulls only digest-qualified references. Normal startup, health,
backup, restore, and application operation do not pull images.

Customer bundles carry the lock and its SHA-256 identity. Provisioning rejects
a bundle whose product manifest and lock disagree. Runtime changes are
release-controlled and require explicit upgrade acknowledgement when the
approved target lock differs.
