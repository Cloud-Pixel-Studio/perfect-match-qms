# Customer Deployment Architecture

Mission 21 establishes a controlled, operator-run customer foundation for
Perfect Match QMS. DEV and Demo remain the only permanent product validation
environments. A customer instance is created from an approved release bundle,
never from a DEV or Demo database.

## Isolation

Each instance uses a normalized slug such as `northstar-precision` and a
dedicated root outside Git:

```text
/opt/perfect-match/instances/<slug>/
  config/       non-secret manifest, Odoo config, environment_id
  secrets/      PostgreSQL, technical admin, and bootstrap secrets (0600)
  identity/     reserved for recovery metadata
  license/      active signed license, outside Git
  activation/   activation request, outside Git
  backups/      customer backup archives, outside Git
  runtime/      release-provided addons and rendered Compose
```

The customer Compose project has its own PostgreSQL volume, Odoo filestore
volume, bridge network, service names, database name, and loopback HTTP port.
PostgreSQL is not published. Odoo is reachable only through the local reverse
proxy or an operator-approved tunnel. `list_db = False` and a database filter
are enabled in the customer Odoo configuration.

## Version and identity

`deployment-manifest.json` records the instance slug, environment type,
product release, database, domain, environment short ID, license ID, and
deployment state. The full environment ID is persisted outside transient
containers and is the same Mission 20 identity consumed by license binding.

## License and data boundary

The customer bundle contains only runtime product assets and public
verification material. License issuance and private signing keys stay outside
the customer runtime. A customer database starts with no operational company,
users, sites, Demo actions, or Demo license. Product/framework definitions may
be included by the approved module set; customer operational records are
created during bootstrap.

## Module selection

`deployment/customer/modules.txt` is the ordered customer product manifest and
now includes the ISO 9001 add-on after `pm_qms_pack_quality`. It is consumed by
the customer bundler and Demo tooling, so dependency order does not drift
between environments. The generic base remains installable without
`pm_qms_iso9001`; the current commercial/Demo bundle is ISO-enabled. Standard
add-ons do not bring Demo records or copied standard text into a clean
customer database.

## Reverse proxy and TLS

DNS is an external prerequisite. `deployment/nginx/customer.conf.example`
provides an HTTP-to-HTTPS redirect and a per-domain upstream. The shared Nginx
reverse proxy may serve multiple customers, but each server block must point to
only its assigned loopback port. Certificate issuance may use the existing
operator-managed Let's Encrypt flow or another managed certificate process.

## Recovery and upgrades

Backups include the database dump, filestore archive, environment identity,
active license, and non-secret metadata with SHA-256 verification. Same-instance
recovery preserves identity and license. A new customer is never a folder copy.
Upgrade means a preflight, verified approved release, successful backup, module
update, health check, and manifest update. Rollback is restore-based after a
database migration; the system does not promise an unsafe magical rollback.
