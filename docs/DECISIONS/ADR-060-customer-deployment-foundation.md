# ADR-060: Isolated Customer Deployment Foundation

- Status: Accepted
- Date: 2026-08-23
- Scope: Mission 21

## Context

Perfect Match QMS needs a repeatable operator-controlled path from an approved
release to an isolated customer environment. DEV and Demo contain product
validation state and must not become customer templates.

## Decision

Customer instances use a normalized slug and an external instance root with
separate secrets, database volume, filestore volume, network, environment
identity, license, backups, and rendered Compose configuration. The reusable
`customer-instance.sh` CLI consumes a canonical module list and approved
release bundle. Odoo remains the runtime and PostgreSQL remains the data store.

The CLI supports guarded initialization, bundle provisioning, clean module
bootstrap, Mission 20 activation/license flow, first Quality Manager bootstrap,
site creation, health, backup/checksum, restore validation, and release-aware
upgrade preflight. Customer Compose uses Odoo 19 and PostgreSQL 15, no public
PostgreSQL port, `list_db = False`, and a database filter. HTTPS remains an
operator-managed shared reverse-proxy concern with per-domain upstreams.

## Consequences

Customer operations are isolated and versioned, but require an operator to
manage DNS, certificates, license issuance, retention, and release bundles.
The deployment foundation is intentionally not a public installer, SaaS
provisioner, billing system, online license server, or product shell.

## Rejected alternatives

- Copying Demo/DEV databases or customer directories for provisioning.
- A shared multi-company customer database as the commercial tenancy model.
- A second deployment architecture that bypasses Mission 20 identity/licensing.
- Automatic tracking of `main` or arbitrary Git commits.
