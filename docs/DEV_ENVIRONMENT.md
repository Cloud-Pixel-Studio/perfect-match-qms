# DEV Environment

Mission 02 establishes a local-only Odoo 19 development environment for Perfect Match Digital QMS.

## Architecture

- Odoo runs from the official `odoo:19.0` Docker image.
- PostgreSQL runs from `postgres:15`.
- Custom addons are mounted from `addons/` into `/mnt/extra-addons`.
- Odoo HTTP and longpolling ports bind to `127.0.0.1` by default.
- Docker network: `pmqms_dev_network`.
- PostgreSQL volume: `pmqms_dev_postgres`.
- Odoo filestore volume: `pmqms_dev_odoo_data`.
- Runtime secrets and generated `odoo.conf` live outside Git under `/opt/perfect-match/secrets/odoo-dev/`.

This stack is isolated from unrelated infrastructure. It does not share
production-like volumes, networks, ports, databases, or environment files.

## Quick Start

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh init-secrets
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh install-mission03
./deployment/scripts/odoo-dev.sh install-mission04
./deployment/scripts/odoo-dev.sh install-mission05
./deployment/scripts/odoo-dev.sh install-mission06
./deployment/scripts/odoo-dev.sh install-mission07
./deployment/scripts/odoo-dev.sh install-mission08
./deployment/scripts/odoo-dev.sh install-mission09
./deployment/scripts/odoo-dev.sh install-mission10
```

Equivalent raw Docker Compose commands:

```bash
docker compose -f deployment/docker/dev/compose.yml up -d
docker compose -f deployment/docker/dev/compose.yml logs -f odoo-dev
docker compose -f deployment/docker/dev/compose.yml down
```

Open Odoo through an SSH tunnel:

```bash
ssh -L 8069:127.0.0.1:8069 administrator-plane@192.168.68.151
```

Then open `http://127.0.0.1:8069` on your workstation.

## Testing

```bash
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh test-mission03
./deployment/scripts/odoo-dev.sh test-mission04
./deployment/scripts/odoo-dev.sh test-mission05
./deployment/scripts/odoo-dev.sh test-mission06
./deployment/scripts/odoo-dev.sh test-mission07
./deployment/scripts/odoo-dev.sh test-mission08
./deployment/scripts/odoo-dev.sh test-mission09
./deployment/scripts/odoo-dev.sh test-mission10
```

The command installs `pm_qms_core` into the `pmqms_test` database with demo data disabled and Odoo tests enabled.

## Odoo Shell

```bash
./deployment/scripts/odoo-dev.sh shell
```

Open an Odoo shell against the DEV database:

```bash
docker compose -f deployment/docker/dev/compose.yml run --rm odoo-dev odoo shell -d pmqms_dev
```

## Module Install and Upgrade

```bash
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh update-core
./deployment/scripts/odoo-dev.sh install-mission03
./deployment/scripts/odoo-dev.sh update-mission03
./deployment/scripts/odoo-dev.sh install-mission04
./deployment/scripts/odoo-dev.sh update-mission04
./deployment/scripts/odoo-dev.sh install-mission05
./deployment/scripts/odoo-dev.sh update-mission05
./deployment/scripts/odoo-dev.sh install-mission06
./deployment/scripts/odoo-dev.sh update-mission06
./deployment/scripts/odoo-dev.sh install-mission07
./deployment/scripts/odoo-dev.sh update-mission07
./deployment/scripts/odoo-dev.sh install-mission08
./deployment/scripts/odoo-dev.sh update-mission08
./deployment/scripts/odoo-dev.sh install-mission09
./deployment/scripts/odoo-dev.sh update-mission09
./deployment/scripts/odoo-dev.sh install-mission10
./deployment/scripts/odoo-dev.sh update-mission10
```

## Retired Oliva Pilot

The Oliva Torras technical pilot was retired in RC6. Its runtime resources were
removed only after a validated local backup. The historical pilot documents in
this repository are retained for traceability, but the pilot compose files,
startup scripts, secrets, database, volumes, network, and ports are no longer
available or supported.

## Health Checks

```bash
./deployment/scripts/odoo-dev.sh ps
docker inspect --format '{{.State.Health.Status}}' pmqms-postgres-dev
docker compose -f deployment/docker/dev/compose.yml logs --tail=100 odoo-dev
```

## Safety Rules

- Do not expose DEV Odoo directly to the Internet.
- Do not use production credentials in the DEV stack.
- Do not connect DEV Odoo to any project-management database.
- Do not commit generated config, database dumps, filestore content, or secrets.
- Do not commit licensed external standard publications or copied external
  requirement text.
- Do not represent historical Oliva pilot validation fixtures as production
  customer data.
