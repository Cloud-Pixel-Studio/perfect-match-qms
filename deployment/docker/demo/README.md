# Perfect Match QMS Demo Docker Stack

This Compose stack runs the disposable fictional product demo environment only.
It uses dedicated containers, volumes, ports, configuration, secrets, and backups.

Default runtime identity:

- Odoo container: `pmqms-odoo-demo`
- PostgreSQL container: `pmqms-postgres-demo`
- Database: `pmqms_demo`
- HTTP port: `8170`
- Longpolling port: `8173`
- Data volume: `pmqms_demo_odoo_data`
- PostgreSQL volume: `pmqms_demo_postgres`

Use `deployment/scripts/odoo-demo.sh` to manage the stack. Do not use this stack
for the Oliva Torras pilot or any real customer data.
