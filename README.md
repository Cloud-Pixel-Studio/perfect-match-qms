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

Mission 05 adds the internal audit foundation: audit programs, individual
audits, normalized scope and criteria, audit team and independence metadata,
planning lines, audit evidence, findings, and controlled finding-to-NCR
integration while preserving NCR-to-CAPA separation.

Mission 06 adds the performance-management foundation: objectives, KPI
definitions, KPI measurements with historical snapshots, KPI trends and
measurement schedules, customer performance, customer satisfaction, supplier
performance, and supplier evaluations.

Mission 07 adds the Management Review engine: controlled review records,
historical input snapshots, management decisions, and follow-up actions. It
consolidates operational QMS data for management review without turning the
review into a live dashboard or copying operational attachments.

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
- `addons/pm_qms_audit/`
- `addons/pm_qms_kpi/`
- `addons/pm_qms_management_review/`
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
./deployment/scripts/odoo-dev.sh install-mission05
./deployment/scripts/odoo-dev.sh test-mission05
./deployment/scripts/odoo-dev.sh install-mission06
./deployment/scripts/odoo-dev.sh test-mission06
./deployment/scripts/odoo-dev.sh install-mission07
./deployment/scripts/odoo-dev.sh test-mission07
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

Internal audit records are also operational records. Audit findings relate to
audits, criteria, evidence, processes, and control instances. Internal
nonconformity findings can create NCR records through a controlled action; CAPA
continues through the existing NCR-to-CAPA pathway.

Performance records are client operational records. Objectives and KPIs may
relate to control instances and processes, but historical KPI measurements live
on `pm.qms.kpi.measurement`, not on reusable `pm.qms.control`. Customer and
supplier performance reuse Odoo `res.partner` as master data instead of
duplicating customer or supplier databases.

Management Review records are client operational records. Review inputs are
snapshots stored on `pm.qms.management.review.input` so completed reviews show
what management actually reviewed at that time. Decisions and follow-up actions
remain separate from the meeting closure, so a review can be completed while
its actions remain open.
