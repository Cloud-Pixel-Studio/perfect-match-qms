# Perfect Match QMS Demo Environment

## Purpose

The demo environment is the official fictional Perfect Match QMS product tour and smoke-test environment. It is separate from the Oliva Torras pilot and must never contain real customer records.

## Runtime

| Item | Value |
| --- | --- |
| Database | `pmqms_demo` |
| URL | `https://demo.invperfectmatch.com/web/login?db=pmqms_demo` |
| Internal URL | `http://192.168.68.151:8170/web/login?db=pmqms_demo` |
| HTTP port | `8170` |
| Longpolling port | `8173` |
| Odoo container | `pmqms-odoo-demo` |
| PostgreSQL container | `pmqms-postgres-demo` |
| PostgreSQL volume | `pmqms_demo_postgres` |
| Odoo filestore volume | `pmqms_demo_odoo_data` |
| Secrets | `/opt/perfect-match/secrets/odoo-demo/` |
| Backups | `/opt/perfect-match/backups/odoo-demo/` |

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

The default demo login is:

```text
demo.qm@perfectmatch.local
```

The password is generated locally and stored outside Git:

```text
/opt/perfect-match/secrets/odoo-demo/demo_admin_password
```

Use `./deployment/scripts/odoo-demo.sh credentials` to print the URL, login, and password file path.

## Perfect Match Brand

The demo login uses the approved Perfect Match Investments LLC primary logo from the brand manual. The logo is loaded into the demo company through Odoo ORM from:

```text
addons/pm_qms_app/static/description/perfect_match_logo_master.png
```

The demo visual layer uses the approved blue as the dominant UI color, magenta for primary actions, and the documented white/off-white operational surfaces. The Oliva pilot remains unbranded by this demo seed.

## Fictional Data

The demo company is `Apex Precision Systems, Inc.`, a fictional US precision manufacturing organization. It includes fictional personas, processes, documents, evidence, risks, NCR, CAPA, audit, KPI, people/training, calibration, customer quality, supplier quality, Cost of Quality, Action Center, and management review scenarios.

No copyrighted standards text, real customer claims, real supplier data, real employees, ITAR, CUI, or confidential files are used.

## Isolation From Oliva

Oliva remains separate:

| Item | Oliva Pilot | Demo |
| --- | --- | --- |
| Database | `pmqms_oliva_pilot` | `pmqms_demo` |
| HTTP port | `8169` | `8170` |
| Purpose | Real pilot validation | Fictional product demonstration |
| Demo data | Never | Yes |

The demo script refuses `pmqms_oliva_pilot`, `pmqms_dev`, `pmqms_test`, and unknown database names.

## Security Rules

- No secrets are committed.
- No global ACL bypass is added.
- Database manager is not exposed by default because `list_db = False` and `dbfilter = ^pmqms_demo$`.
- Demo data is created through Odoo ORM and workflow-aware source records.
- Action Center rows are never manually fabricated.

## Backup Policy

Demo backups, when needed, are stored under `/opt/perfect-match/backups/odoo-demo/` and do not mix with Oliva pilot backups.
