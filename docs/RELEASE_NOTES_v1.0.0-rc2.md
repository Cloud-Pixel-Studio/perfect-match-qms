# Release Notes v1.0.0-rc2

Release candidate date: 2026-08-21

## Summary

`v1.0.0-rc2` is the Perfect Match QMS Product Experience and Guided Implementation release candidate.

This release freezes the reusable product baseline after the application shell, executive dashboard, guided implementation workflow, readiness center, and Perfect Match-specific activity UX were completed.

Readiness in Perfect Match QMS reflects recorded implementation status and does not constitute certification, certification-body approval, or a guarantee of compliance.

## Highlights

- Unified Perfect Match QMS application experience.
- Executive QMS dashboard with implementation, evidence, activity, operational health, performance, and management-review indicators.
- Guided QMS implementation workflow for generated customer implementation projects.
- Pack-driven implementation areas and framework-pack architecture.
- Proprietary Perfect Match implementation guidance for controls.
- Controls, activities, and evidence integrated into one implementation experience.
- Gap visibility for controls, missing evidence, and open activities.
- Readiness Center with area progress and deterministic recommended next actions.
- Historical readiness assessments preserved as snapshots.
- Perfect Match Activity UX backed by Odoo `project.task` as the execution engine.
- Native Odoo Project remains available for authorized Odoo users.
- QMS operational modules remain integrated under the product shell:
  - Documents
  - Evidence
  - Risk and Opportunities
  - NCR
  - CAPA
  - Internal Audit
  - Objectives and KPI
  - Customer Performance
  - Supplier Performance
  - Management Review
- Implementation generator, shared-control deduplication, and existing migration tooling remain part of the baseline.

## Included Addons

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
- `pm_qms_app`

Addon manifest versions continue to follow the repository's Odoo-specific module versioning strategy. The Git release tag for this product baseline is `v1.0.0-rc2`.

## Validation Summary

- Canonical main baseline validated before release documentation: `5b2c14cfec6e1d0434fa273b8ded1e6a0444b134`.
- GitHub Actions `QMS CI` on that baseline passed.
- Local release validation passed:
  - Python compile validation
  - Manifest and XML validation
  - Secret scan
  - External-standard content safety scan
  - Shell syntax validation
  - Git whitespace diff validation
  - Odoo Mission 11 tests
  - Odoo Mission 12 tests
  - Odoo Mission 12.1 tests
  - Existing DEV database upgrade validation
- Odoo test baseline: 86 post-tests, 0 failures, 0 errors.

## Pilot Validation

The Oliva Torras pilot remains a validation environment only. It is not product hardcoding and is not part of reusable customer deployment data.

RC2 pilot validation confirmed:

- Pilot HTTP health: 200
- Implementation areas: 6
- Implementation controls: 37
- Generated activities/tasks: 74
- Required evidence expectations: 37
- Accepted evidence records for readiness: 1
- Missing evidence count: 36
