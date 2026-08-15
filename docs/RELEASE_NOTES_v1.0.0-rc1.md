# Release Notes v1.0.0-rc1

Release candidate date: 2026-08-15

## Summary

`v1.0.0-rc1` validates Perfect Match Digital QMS as a deployable technical
pilot for `Oliva Torras USA, Inc.`

This release candidate is not a customer production go-live and does not claim
certification, compliance, or acceptance by Oliva Torras.

## Included

- Isolated Oliva pilot Odoo stack with dedicated PostgreSQL database, Docker
  network, volumes, secrets, and localhost-only ports.
- Full QMS addon stack including:
  - `pm_qms_core`
  - `pm_qms_documents`
  - `pm_qms_evidence`
  - `pm_qms_risk`
  - `pm_qms_ncr`
  - `pm_qms_capa`
  - `pm_qms_audit`
  - `pm_qms_kpi`
  - `pm_qms_management_review`
  - `pm_qms_implementation`
  - `pm_qms_pack_quality`
  - `pm_qms_migration`
- `PM-QMS-QUALITY` version `1.0` deployed into an Oliva technical pilot project.
- 37 generated implementation controls.
- 74 generated implementation tasks.
- 37 required evidence expectations.
- Controlled document and evidence CSV import wizards.
- Pilot backup and restore scripts.
- Mission 10 automated test target and CI coverage.
- Oliva pilot runbook, implementation guide, onboarding checklist, and migration
  inventory template.

## Pilot Validation Results

Mission 10 validation records were labeled `PILOT VALIDATION`.

- Organization: `OTUS:Oliva Torras USA, Inc.`
- Project: `PM-IMP-00002`
- Pack: `PM-QMS-QUALITY:1.0:active`
- Controls: 37
- Generated tasks: 74
- Required evidence: 37
- Readiness before validation: 0.0000 percent
- Readiness after one validated control: 2.7027 percent
- Evidence import rejected direct `accepted` state: true
- Other-company attachment isolation: true
- Approved external mappings: 0

## Explicit Non-Claims

- No real Oliva production documents were imported.
- No real Oliva production evidence was accepted.
- No real Oliva users, process owners, suppliers, customers, KPIs, risks, NCRs,
  CAPAs, audits, or management decisions were invented.
- External standard mapping remains 0 percent approved until a human-approved
  metadata CSV is supplied.
- This release does not provide customer portal, AI assistant, n8n production
  automation, or multi-standard pack functionality.
- No public DNS/TLS route was configured for the pilot Odoo stack.

## Upgrade Notes

For DEV validation:

```bash
./deployment/scripts/odoo-dev.sh install-mission10
./deployment/scripts/odoo-dev.sh test-mission10
```

For Oliva pilot validation:

```bash
./deployment/scripts/odoo-pilot.sh install
./deployment/scripts/odoo-pilot.sh configure-client
./deployment/scripts/odoo-pilot.sh run-readiness
./deployment/scripts/odoo-pilot.sh health
```
