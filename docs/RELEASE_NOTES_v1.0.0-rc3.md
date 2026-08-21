# Perfect Match QMS v1.0.0-rc3

Operational QMS Expansion Release Candidate

Release candidate date: 2026-08-21

## Summary

`v1.0.0-rc3` is the Perfect Match QMS operational expansion release candidate.

This release freezes the reusable product baseline after the complete product visual surface, people/training/competency management, and equipment/calibration management capabilities were completed.

Readiness in Perfect Match QMS reflects recorded implementation status and does not constitute certification, certification-body approval, or a guarantee of compliance.

## Highlights

- Complete Perfect Match QMS product visual surface.
- Unified application shell and executive dashboard.
- Guided implementation workflow with implementation areas, proprietary guidance, controls, activities, evidence, gaps, readiness center, historical readiness, and deterministic next actions.
- QMS operational modules for documents, evidence, risk, NCR, CAPA, internal audit, objectives, KPI, customer performance, supplier performance, and management review.
- QMS People with configurable roles, role assignments, competencies, competency matrix, assessments, training records, qualifications, expiration monitoring, and revision-specific document acknowledgments.
- Equipment and monitoring-resource register.
- Calibration and verification scheduling.
- Calibration certificates and evidence traceability.
- Due, due-soon, overdue, and current calibration monitoring.
- Out-of-tolerance workflow with automatic equipment quarantine.
- Calibration impact assessment with potential exposure window.
- Future-compatible affected-record references.
- NCR and CAPA traceability from equipment, calibration events, and impact assessments.
- Dashboard and Management Review integrations for people and calibration attention items.

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
- `pm_qms_people`
- `pm_qms_calibration`

Addon manifest versions continue to follow the repository's Odoo-specific module versioning strategy. The Git product release tag for this product baseline is `v1.0.0-rc3`.

## Validation Summary

Canonical main validated before RC3 release documentation:

```text
5cb9dc2d029988fdde9d46883bf89a3e660f8a51
```

Local release validation passed:

- Python compile validation
- Addon manifest and XML validation
- Secret scan
- External-standard content safety scan
- Shell syntax validation
- Git whitespace diff validation
- Docker Compose configuration validation
- Existing DEV database upgrade validation
- Odoo Mission 15 regression suite

Odoo test baseline:

- 103 post-tests
- 0 failures
- 0 errors

GitHub Actions:

- Workflow: `QMS CI`
- Run: `32530039351`
- Result: PASS

## Pilot Validation

The Oliva Torras pilot remains a validation environment only. It is not product hardcoding and is not part of reusable customer deployment data.

RC3 pilot validation confirmed:

- Pilot backup: `/opt/perfect-match/backups/odoo-oliva-pilot/pmqms-oliva-pilot-20260821T224528Z.tar.gz`
- Pilot update: PASS
- Pilot HTTP health: 200
- Implementation areas: 6
- Implementation controls: 37
- Generated activities/tasks: 74
- Required evidence expectations: 37
- People records: 0
- Calibration equipment: 0
- Calibration events: 0
- Calibration impact assessments: 0

No fictional calibration demo data was seeded into the pilot.

## Known Issues

- GitHub Actions reports a non-blocking warning that some third-party actions targeting Node.js 20 are forced to run on Node.js 24. This is release technical debt and does not block RC3.
- RC3 is still a pre-release candidate, not a final stable release.
- Perfect Match QMS readiness metrics do not claim external certification, guaranteed compliance, or certification-body approval.
