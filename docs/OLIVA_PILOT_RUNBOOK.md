# Oliva Torras Pilot Runbook

This runbook operates the isolated technical pilot for `Oliva Torras USA, Inc.`

The pilot is a validation environment for Perfect Match Digital QMS. It is not
a customer production go-live, it does not contain authorized Oliva production
records, and it does not claim ISO certification or external compliance.

## Environment

- Host path: `/opt/perfect-match/perfect-match-qms`
- Docker Compose file: `deployment/docker/pilot/compose.yml`
- Odoo database: `pmqms_oliva_pilot`
- Odoo HTTP: `127.0.0.1:8169`
- Odoo longpolling: `127.0.0.1:8172`
- PostgreSQL container: `pmqms-postgres-oliva-pilot`
- Odoo container: `pmqms-odoo-oliva-pilot`
- Docker network: `pmqms_oliva_pilot_network`
- PostgreSQL volume: `pmqms_oliva_pilot_postgres`
- Odoo filestore volume: `pmqms_oliva_pilot_odoo_data`
- Secrets directory: `/opt/perfect-match/secrets/odoo-oliva-pilot`

The pilot ports bind to localhost on the VM. Public DNS and TLS routing for the
pilot were not configured in Mission 10.

## Start And Health

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-pilot.sh init-secrets
./deployment/scripts/odoo-pilot.sh config
./deployment/scripts/odoo-pilot.sh up
./deployment/scripts/odoo-pilot.sh health
```

Open the pilot from a workstation with an SSH tunnel:

```bash
ssh -L 8169:127.0.0.1:8169 administrator-plane@192.168.68.151
```

Then browse to `http://127.0.0.1:8169/web/login?db=pmqms_oliva_pilot`.

## Install Or Update

```bash
./deployment/scripts/odoo-pilot.sh install
./deployment/scripts/odoo-pilot.sh configure-client
./deployment/scripts/odoo-pilot.sh run-readiness
```

`configure-client` verifies:

- Odoo company name: `Oliva Torras USA, Inc.`
- QMS organization code: `OTUS`
- Implementation project: `Oliva Torras QMS Technical Pilot`
- Active pack: `PM-QMS-QUALITY` version `1.0`
- Generated controls: 37
- Generated tasks: 74
- Required evidence records: 37

## Validation Baseline

Mission 10 validation created records labeled `PILOT VALIDATION`. These are
technical validation records only. They are not real customer procedures,
owners, suppliers, KPIs, risks, NCRs, CAPAs, audits, or review decisions.

Validated baseline:

- Generated project: `PM-IMP-00002`, state `in_progress`
- Pre-change readiness assessment: `PM-RA-00007`, 0.0000 percent
- Post-validation readiness assessment: `PM-RA-00008`, 2.7027 percent
- Approved mapping count: 0
- Evidence import blocked direct `accepted` state: true
- Attachment isolation for other-company user: true

The readiness increase represents one pilot validation control with accepted
evidence and closed generated tasks. The remaining gap is expected until Oliva
provides authorized real implementation data and approvals.

## Backup

```bash
./deployment/scripts/backup-oliva-pilot.sh backup
```

Backups are written outside Git under:

```text
/opt/perfect-match/backups/odoo-oliva-pilot
```

Each backup includes:

- PostgreSQL custom dump
- Odoo filestore archive
- Pilot Odoo configuration copy
- SHA-256 checksum file

## Restore Rehearsal

Restore only to a disposable database unless a controlled change explicitly
authorizes replacing the active pilot database.

```bash
./deployment/scripts/restore-oliva-pilot.sh \
  --backup /opt/perfect-match/backups/odoo-oliva-pilot/pmqms-oliva-pilot-YYYYMMDDTHHMMSSZ.tar.gz \
  --target-db pmqms_oliva_restore_m10 \
  --confirm-target-db pmqms_oliva_restore_m10 \
  --replace-existing \
  --drop-after-restore
```

## Safety Rules

- Do not expose pilot Odoo directly to the Internet without a separate DNS,
  reverse-proxy, and TLS change.
- Do not store customer credentials, database dumps, or backup archives in Git.
- Do not mark external mappings approved without a human-approved CSV containing
  only allowed reference metadata.
- Do not represent `PILOT VALIDATION` records as Oliva production data.
- Use Odoo ORM, import wizards, or documented scripts for application data.
- Use Plane API, Compose, or MCP for Plane work items; never update Plane
  PostgreSQL directly.
