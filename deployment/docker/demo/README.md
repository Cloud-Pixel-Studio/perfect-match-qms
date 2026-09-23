# Perfect Match QMS Demo Docker Stack

This Compose stack runs the disposable fictional product demo environment only.
It uses dedicated containers, volumes, ports, configuration, secrets, and backups.

Default runtime identity:

- Compose project: `pmqms-demo`
- Odoo container: Compose-generated from project and service name
- PostgreSQL container: Compose-generated from project and service name
- Database: `pmqms_demo`
- HTTP port: `8170`
- Longpolling port: `8173`
- Data volume: `pmqms_demo_odoo_data`
- PostgreSQL volume: `pmqms_demo_postgres`
- Network: `pmqms_demo_network`
- Secrets: `/opt/perfect-match/secrets/odoo-demo`
- Backups: `/opt/perfect-match/backups/odoo-demo`

The launcher defaults to `PMQMS_DEMO_INSTANCE=demo`. For a second isolated
stack, set `PMQMS_DEMO_INSTANCE=demo2` and use the Demo2 values documented in
[`docs/DEMO_ENVIRONMENT.md`](../../../docs/DEMO_ENVIRONMENT.md). The project,
container names, database, volumes, network, secrets, backup path, activation
request path, license file, and runtime lock must remain instance-specific.
Each instance requires its own environment UUID and signed `.pmql`; do not
reuse any database, volume, secret, license, or backup between instances.

Use `deployment/scripts/odoo-demo.sh` to manage the stack. Do not use this stack
for the Oliva Torras pilot or any real customer data.
