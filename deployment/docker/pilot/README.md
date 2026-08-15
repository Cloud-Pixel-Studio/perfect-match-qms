# Oliva Torras Pilot Docker Stack

This directory defines the production-like local pilot stack for
`pmqms_oliva_pilot`.

It is intentionally separate from:

- Plane
- PMQMS DEV
- Plane PostgreSQL
- DEV PostgreSQL
- DEV Odoo filestore

Default services:

- `pmqms-postgres-oliva-pilot`
- `pmqms-odoo-oliva-pilot`

Default network and volumes:

- `pmqms_oliva_pilot_network`
- `pmqms_oliva_pilot_postgres`
- `pmqms_oliva_pilot_odoo_data`

The Odoo HTTP ports bind to `127.0.0.1` by default. Do not publish this stack
through Nginx or DNS until customer launch is authorized.

Use:

```bash
./deployment/scripts/odoo-pilot.sh install
./deployment/scripts/odoo-pilot.sh configure-client
./deployment/scripts/odoo-pilot.sh health
```
