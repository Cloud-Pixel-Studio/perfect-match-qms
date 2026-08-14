# Perfect Match Digital QMS

Perfect Match Digital QMS is a proprietary digital management system implementation platform for Perfect Match Investments LLC.

The product will help organizations implement, operate, monitor, and improve management systems through Perfect Match proprietary methods, controls, workflows, templates, evidence expectations, and implementation guidance.

## IP Boundary

This repository must not contain copyrighted ISO, IATF, AS, SAE, CMMC, or other third-party standard text unless a valid license explicitly permits it and use is authorized.

Perfect Match proprietary controls are stored separately from external standard references and mappings.

## Target Platform

- Odoo 19 Self-Hosted.
- Python and Odoo ORM.
- PostgreSQL.
- Odoo Owl, JavaScript, XML/QWeb.
- Docker, Docker Compose, Linux, Nginx, TLS.
- n8n for external integration automation.
- OpenAI API for controlled QMS assistance.
- Plane for project management.

## Current Status

Mission 02 establishes the isolated Odoo DEV environment and the first installable
`pm_qms_core` addon.

Mission 03 adds the client implementation layer, controlled documents, document
revisions, and actual evidence records.

Mission 04 adds operational hardening, risk and opportunity management,
nonconformity management, CAPA, CI quality gates, and DEV backup/restore
validation.

Core paths:

- `deployment/docker/dev/compose.yml`
- `deployment/scripts/odoo-dev.sh`
- `docs/DEV_ENVIRONMENT.md`
- `docs/TESTING.md`
- `docs/ARCHITECTURE.md`
- `addons/pm_qms_core/`
- `addons/pm_qms_documents/`
- `addons/pm_qms_evidence/`
- `addons/pm_qms_risk/`
- `addons/pm_qms_ncr/`
- `addons/pm_qms_capa/`
- `.github/workflows/qms-ci.yml`

## DEV Quick Start

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh init-secrets
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh install-mission03
./deployment/scripts/odoo-dev.sh test-mission03
./deployment/scripts/odoo-dev.sh install-mission04
./deployment/scripts/odoo-dev.sh test-mission04
```

Raw Docker Compose commands use the same compose file:

```bash
docker compose -f deployment/docker/dev/compose.yml up -d
docker compose -f deployment/docker/dev/compose.yml logs -f odoo-dev
docker compose -f deployment/docker/dev/compose.yml down
```

The DEV stack uses `pmqms_dev_network`, `pmqms_dev_postgres`, and
`pmqms_dev_odoo_data`. It is intentionally separate from Plane.

## Framework vs Client Implementation

`pm.qms.control` defines reusable Perfect Match methodology. It remains a
framework definition.

`pm.qms.control.instance` represents how a specific organization implements a
framework control. Documents and evidence attach to the client implementation,
not to copied external standard text.

Risk, NCR, and CAPA records are also client operational records. They relate to
control instances and client evidence/documents without mutating reusable
framework controls.
