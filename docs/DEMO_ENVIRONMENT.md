# Perfect Match QMS Demo Environment

## Purpose

The demo environment is the official fictional Perfect Match QMS product tour,
smoke-test, and customer-facing validation environment. It must never contain
real customer records. The Oliva Torras pilot is retired and is not an active
peer environment.

## Runtime

| Item | Value |
| --- | --- |
| Instance | `demo` |
| Database | `pmqms_demo` |
| URL | `https://demo.invperfectmatch.com/web/login?db=pmqms_demo` |
| Internal URL | `http://192.168.68.151:8170/web/login?db=pmqms_demo` |
| HTTP port | `8170` |
| Longpolling port | `8173` |
| Compose project | `pmqms-demo` |
| Odoo container | Compose-derived (`pmqms-demo-odoo-demo-1`) |
| PostgreSQL container | Compose-derived (`pmqms-demo-postgres-demo-1`) |
| PostgreSQL volume | `pmqms_demo_postgres` |
| Odoo filestore volume | `pmqms_demo_odoo_data` |
| Secrets | `/opt/perfect-match/secrets/odoo-demo/` |
| Backups | `/opt/perfect-match/backups/odoo-demo/` |
| Runtime lock | `deployment/runtime/runtime-lock.json` in this checkout |

## Multiple isolated Demo instances

The launcher accepts `PMQMS_DEMO_INSTANCE`; the default `demo` preserves the
original database, secret/backup paths, ports, volumes, network, project, and
runtime lock. Instance names are restricted to lowercase letters, digits, and
hyphens, beginning with a letter. The database, project, volumes, and network
are derived from the instance name and mismatched overrides are rejected.

Demo2 uses an explicit isolated environment:

```bash
export PMQMS_DEMO_INSTANCE=demo2
export PMQMS_DEMO_DB=pmqms_demo2
export PMQMS_DEMO_SECRETS_DIR=/opt/perfect-match/secrets/odoo-demo-isolated
export PMQMS_DEMO_BACKUP_DIR=/opt/perfect-match/backups/odoo-demo-isolated
export PMQMS_DEMO_COMPOSE_PROJECT=pmqms-demo2
export PMQMS_DEMO_POSTGRES_VOLUME=pmqms_demo2_postgres
export PMQMS_DEMO_ODOO_VOLUME=pmqms_demo2_odoo_data
export PMQMS_DEMO_NETWORK=pmqms_demo2_network
export ODOO_DEMO_HTTP_PORT=8171
export ODOO_DEMO_LONGPOLLING_PORT=8174
./deployment/scripts/odoo-demo.sh show-config
```

`show-config` validates and prints the effective paths and resource names
without creating files or changing permissions. Review it before running
`config` or `init-secrets`; those commands print the effective paths before
making any filesystem changes. A non-default instance stores its own copy of
the tracked runtime lock under its secrets root. The Compose project derives
container names automatically; no fixed `container_name` is used.

On initialization the launcher claims each secrets and backup root with a
non-secret `.pmqms-demo-instance-owner` marker. Existing markers must match the
selected instance. A custom non-empty root without a marker is refused; the
historical default Demo roots may be adopted once for backward compatibility.
This prevents two instances from sharing relocated roots even when paths are
outside the standard `/opt` locations.

Every instance must have its own environment UUID, activation request, signed
`.pmql`, secrets directory, database, Compose project, network, volumes,
runtime-lock copy, and backup directory. Never share a database, volume,
secret, license, UUID, activation request, or backup location between Demo1
and Demo2. Non-default instances are rejected if any effective path overlaps
the original Demo secrets or backup roots, or if they resolve to
`pmqms_demo`.

## Commands

Run from `/opt/perfect-match/perfect-match-qms`.

```bash
./deployment/scripts/odoo-demo.sh init-secrets
./deployment/scripts/odoo-demo.sh reset-demo
./deployment/scripts/odoo-demo.sh seed-demo
./deployment/scripts/odoo-demo.sh validate-demo
./deployment/scripts/odoo-demo.sh health
./deployment/scripts/odoo-demo.sh credentials
```

`reset-demo` deletes only the demo PostgreSQL and Odoo filestore volumes, rebuilds `pmqms_demo`, installs the full Perfect Match QMS addon set, and runs the demo seed.

## Login

The default demo administrator login is:

```text
admin
```

The demo administrator password is stored outside Git:

```text
/opt/perfect-match/secrets/odoo-demo/demo_admin_password
```

Use `./deployment/scripts/odoo-demo.sh credentials` to print the URL, login, and password file path.

## Perfect Match Brand

The demo login uses the approved Perfect Match Investments LLC primary logo from the brand manual. The logo is loaded into the demo company through Odoo ORM from:

```text
addons/pm_qms_app/static/description/perfect_match_logo_master.png
```

The demo visual layer uses the approved blue as the dominant UI color, magenta for primary actions, and the documented white/off-white operational surfaces. Historical Oliva pilot records were not part of this demo seed.

## Fictional Data

The demo company is `Apex Precision Systems, Inc.`, a fictional US precision manufacturing organization. It includes fictional personas, processes, documents, evidence, risks, NCR, CAPA, audit, KPI, people/training, calibration, customer quality, supplier quality, Cost of Quality, Action Center, and management review scenarios.

No copyrighted standards text, real customer claims, real supplier data, real employees, ITAR, CUI, or confidential files are used.

## Retired Pilot Boundary

The former Oliva pilot was retired in RC6 after a validated local backup. Its
runtime database, containers, volumes, network, secrets, and ports were
removed. The final archive is retained outside Git under the VM retirement
backup directory and must never be committed or uploaded.

The launcher accepts only the database name derived from the validated
instance slug (for example, `demo` -> `pmqms_demo`, `demo2` ->
`pmqms_demo2`). It refuses database-name overrides that could cross instance
boundaries, including retired pilot, development, test, and shared Demo names.

## Security Rules

- No secrets are committed.
- No global ACL bypass is added.
- Database manager is not exposed by default because `list_db = False` and the configured `dbfilter` matches only the selected instance database.
- Demo data is created through Odoo ORM and workflow-aware source records.
- Action Center rows are never manually fabricated.

## Backup Policy

Each instance writes backups only under its effective backup directory. Demo1
uses `/opt/perfect-match/backups/odoo-demo/`; Demo2 uses
`/opt/perfect-match/backups/odoo-demo-isolated/`.
