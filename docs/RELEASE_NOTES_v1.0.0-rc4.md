# Perfect Match QMS v1.0.0-rc4

Customer and Supplier Quality Release Candidate

Release candidate date: 2026-08-22

## Summary

`v1.0.0-rc4` is the Perfect Match QMS customer and supplier quality release candidate.

This release freezes the reusable product baseline after Mission 16, adding customer complaints, quality alerts, 8D case management, supplier issues, SCAR, customer/supplier quality dashboard signals, and management review integration. It also includes the post-Mission16 CAPA 5 Why inline-list UX correction.

Readiness in Perfect Match QMS reflects recorded implementation status and does not constitute certification, certification-body approval, or a guarantee of compliance.

## Highlights

- Customer complaint workflow with containment, response tracking, NCR linkage, 8D creation, quality alerts, and controlled closure.
- Quality alert workflow with severity, containment notes, responsible owner, closure controls, and dashboard visibility.
- 8D case management with structured D0-D8 sections, root-cause analysis, CAPA linkage, effectiveness review, and closure controls.
- Supplier issue workflow with containment, NCR linkage, optional SCAR creation, and controlled closure.
- SCAR workflow with supplier response history, returned revisions, accepted responses, effectiveness review, explicit CAPA creation, and closure controls.
- Existing NCR and CAPA remain the authoritative engines; customer and supplier quality records link to them instead of replacing them.
- Dashboard and Management Review integrations for customer and supplier quality attention items.
- Security and company-isolation rules across the customer and supplier quality surface.
- CAPA 5 Why inline list now displays sequence, question, and answer columns instead of a generic ID-only row.

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
- `pm_qms_customer_quality`

Addon manifest versions continue to follow the repository's Odoo-specific module versioning strategy. The Git product release tag for this product baseline is `v1.0.0-rc4`.

## Validation Summary

Canonical main validated before RC4 release documentation:

```text
2c2fb856a07e3687b576c7f09bd02454eae6ef8f
```

Local release validation passed:

- Python compile validation
- Addon manifest and XML validation
- Secret scan
- External-standard content safety scan
- Shell syntax validation
- Git whitespace diff validation
- Docker Compose configuration validation
- DEV install validation for the current Mission 16 stack
- Existing DEV database upgrade validation
- Odoo Mission 16 regression suite on clean `pmqms_test`

Odoo test baseline:

- 110 post-tests
- 0 failures
- 0 errors

GitHub Actions before RC4 release documentation:

- Workflow: `QMS CI`
- Run: `32550416651`
- Commit: `2c2fb856a07e3687b576c7f09bd02454eae6ef8f`
- Result: PASS

## Pilot Validation

The Oliva Torras pilot remains a validation environment only. It is not product hardcoding and is not part of reusable customer deployment data.

RC4 pilot validation confirmed:

- Pilot backup: `/opt/perfect-match/backups/odoo-oliva-pilot/pmqms-oliva-pilot-20260822T041155Z.tar.gz`
- Pilot update: PASS
- Pilot HTTP health: 200
- Implementation controls: 37
- Generated activities/tasks: 74
- Required evidence expectations: 37
- Readiness: 2.7027027027027026
- People records: 0
- Training records: 0
- Qualification records: 0
- Calibration equipment: 0
- Calibration events: 0
- Calibration impact assessments: 0
- Customer complaints: 0
- Quality alerts: 0
- 8D cases: 0
- Supplier issues: 0
- SCAR records: 0
- QMS action/view smoke: 72 actions, 65 models, 0 view errors
- CAPA 5 Why inline columns: `sequence`, `question`, `answer`

No fictional customer/supplier quality, people, or calibration demo data was seeded into the pilot.

## Known Issues

- GitHub Actions reports a non-blocking warning that some third-party actions targeting Node.js 20 are forced to run on Node.js 24. This is release technical debt and does not block RC4.
- GitHub Actions also reports a non-blocking `punycode` deprecation warning from the Node runtime path.
- RC4 is still a pre-release candidate, not a final stable release.
- Perfect Match QMS readiness metrics do not claim external certification, guaranteed compliance, or certification-body approval.
