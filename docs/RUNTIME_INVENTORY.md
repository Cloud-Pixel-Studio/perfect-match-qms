# Runtime Inventory and Reproducibility Policy

Mission `RUNTIME-HARDENING-01` records the persistent application runtime used
by the Perfect Match Demo and DEV environments. The inventory was observed on
2026-08-30 without pulling or changing images.

| Environment / surface | Previous reference | Locked reference | Impact |
| --- | --- | --- | --- |
| Demo Odoo | `odoo:19.0` | `odoo:19.0@sha256:94a4f480b8039dc9ca2bca9e77e59f97d3311f66e2aad663cf2670be9c66d4ea` | Persistent service is tied to the validated image digest. |
| Demo PostgreSQL | `postgres:15` | `postgres:15@sha256:0dda651c259bfe50e2bcc28ca23d1fcca772fa90b0210803aa7b97379ccf4e85` | Persistent database runtime is tied to the validated image digest. |
| DEV Odoo | `odoo:19.0` | Same locked Odoo reference as Demo | DEV and Demo use the same validated application runtime. |
| DEV PostgreSQL | `postgres:15` | Same locked PostgreSQL reference as Demo | DEV and Demo use the same validated database runtime. |
| Customer Odoo | `odoo:19.0` in the customer template/helper | Same locked Odoo reference | Provisioning and compose rendering fail closed without the lock. |
| Customer PostgreSQL | `postgres:15` in the customer template | Same locked PostgreSQL reference | Provisioning and customer readiness verify the exact image identity. |
| Customer utility | Floating `alpine:3.20` helper calls | `alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc` | Backup, license, and lifecycle helpers use the approved utility image. |

The locked values are stored in `deployment/runtime/runtime-lock.json`. Compose
files use `pull_policy: never`; the scripts expose an explicit `runtime-fetch`
command and `runtime-verify` checks the local image store without registry
access. Normal start, update, backup, restore, and readiness paths do not pull
or upgrade images implicitly.

`deployment/runtime/runtime-lock.json` is included in customer bundles and its
SHA-256 plus image references are recorded in product and deployment manifests.
Customer upgrade preflight compares the current and target lock and requires
explicit `--approve-runtime-change` before a runtime change is accepted.

This mission does not modify Demo data, database volumes, licenses, business
records, or Odoo addon behavior. Plane, Odoo upstream, and unrelated utility
containers are outside this runtime lock boundary.
