# PMQMS Odoo DEV

This Compose stack runs the local Perfect Match Digital QMS Odoo development environment.

The Odoo and PostgreSQL services resolve their immutable image references from
`deployment/runtime/runtime-lock.json`. Use `./deployment/scripts/odoo-dev.sh
runtime-fetch` as the explicit preparation step on a new host; `up`, `health`,
and tests do not pull images implicitly.

## Architecture

```text
PMQMS DEV

Docker Compose
|-- odoo-dev
`-- postgres-dev
```

The stack is isolated from Plane:

- dedicated network: `pmqms_dev_network`;
- dedicated PostgreSQL volume: `pmqms_dev_postgres`;
- dedicated Odoo filestore volume: `pmqms_dev_odoo_data`;
- Odoo binds to `127.0.0.1` by default.

## Commands

Run from the repository root:

```bash
./deployment/scripts/odoo-dev.sh init-secrets
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh logs
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh update-core
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh down
```

Equivalent direct Docker Compose commands:

```bash
docker compose -f deployment/docker/dev/compose.yml up -d
docker compose -f deployment/docker/dev/compose.yml logs -f odoo-dev
docker compose -f deployment/docker/dev/compose.yml exec odoo-dev bash
docker compose -f deployment/docker/dev/compose.yml exec postgres-dev psql -U odoo -d postgres
docker compose -f deployment/docker/dev/compose.yml down
```

Install, upgrade, and test the core addon through the wrapper so runtime
permissions and local secrets are prepared first:

```bash
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh update-core
./deployment/scripts/odoo-dev.sh test-core
```

Use an SSH tunnel from your workstation:

```bash
ssh -L 8069:127.0.0.1:8069 administrator-plane@192.168.68.151
```

Then browse to `http://127.0.0.1:8069`.
