# ADR-055: Dedicated Product Demo Environment

## Status

Accepted

## Context

Perfect Match QMS now has a real Oliva Torras pilot database used for customer validation. The product also needs a rich fictional environment for product owner review, demos, screenshots, training, smoke testing, and sales walkthroughs.

The Oliva pilot cannot be used for demo data. It must remain a real pilot environment with no fictional records.

## Decision

Create a dedicated disposable demo environment with its own Odoo and PostgreSQL stack:

- Database: `pmqms_demo`
- Odoo container: `pmqms-odoo-demo`
- PostgreSQL container: `pmqms-postgres-demo`
- HTTP port: `8170`
- Longpolling port: `8173`
- Dedicated filestore volume: `pmqms_demo_odoo_data`
- Dedicated database volume: `pmqms_demo_postgres`
- Dedicated secrets path: `/opt/perfect-match/secrets/odoo-demo`
- Dedicated backup path: `/opt/perfect-match/backups/odoo-demo`

The demo is seeded through Odoo ORM in `deployment/demo/seed_demo.py`. The seed refuses any database other than `pmqms_demo` and creates only fictional Apex Precision Systems data.

## Consequences

The product owner gets one coherent full-product demonstration environment while Oliva remains isolated for real pilot validation. Demo reset is intentionally destructive only for the demo stack and hard-refuses known non-demo databases.

The current product does not yet contain a first-class Site model. The demo records the intended three-site concept as metadata and documents that limitation rather than inventing unsupported site records or extra companies.
