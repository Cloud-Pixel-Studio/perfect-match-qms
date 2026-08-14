# Docker Development Environment

This directory contains the local Odoo development Compose stack for Perfect Match Digital QMS.

## Services

- `odoo`: Odoo 19 Community, bound to `127.0.0.1:8069` by default.
- `db`: PostgreSQL 15, private to the Docker network.
- Named volumes: `pmqms_odoo_dev_data` and `pmqms_odoo_dev_db`.

The stack is intentionally isolated from the existing Plane deployment. It does not reuse Plane containers, volumes, networks, ports, or credentials.

## Secrets

Runtime secrets are generated outside Git under:

`/opt/perfect-match/secrets/odoo-dev/`

Do not commit generated `odoo.conf`, Postgres passwords, database dumps, or filestore data.

## Commands

Run from the repository root:

```bash
./deployment/scripts/odoo-dev.sh init-secrets
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh logs
./deployment/scripts/odoo-dev.sh down
```

Access is local-only by default. Use an SSH tunnel if you need browser access from another machine:

```bash
ssh -L 8069:127.0.0.1:8069 administrator-plane@192.168.68.151
```
