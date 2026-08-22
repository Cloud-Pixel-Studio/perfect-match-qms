# Release Baseline v1.0.0-rc4

Release: `v1.0.0-rc4`

Release date: 2026-08-22

Release type: Customer and supplier quality release candidate

## Baseline Source

Validated canonical main before release documentation:

```text
2c2fb856a07e3687b576c7f09bd02454eae6ef8f
```

The authoritative RC4 source is the pushed annotated Git tag `v1.0.0-rc4` in the canonical GitHub repository. The final tag target is verified at release time and reported in the release evidence.

Canonical repository:

```text
https://github.com/Cloud-Pixel-Studio/perfect-match-qms
```

## Product Scope

RC4 freezes the reusable Perfect Match QMS baseline containing:

- Perfect Match QMS application shell
- Unified navigation
- Executive dashboard
- Complete product visual surface
- Guided implementation projects
- Framework packs and pack versions
- Implementation areas
- Proprietary Perfect Match guidance
- Controls, activities, evidence, gaps, readiness center, historical readiness, and deterministic next actions
- Document control, document revisions, and evidence
- Risk and opportunities
- NCR and CAPA
- Internal audit
- Objectives, KPI, customer performance, and supplier performance
- Management Review
- QMS people, configurable roles, competencies, competency matrix, assessments, training, qualifications, and revision-specific document acknowledgments
- Equipment register, monitoring resources, calibration planning, calibration events, verification events, certificates, due/overdue monitoring, out-of-tolerance workflow, quarantine, impact assessment, exposure window, and NCR/CAPA traceability
- Customer complaints, quality alerts, 8D cases, supplier issues, SCAR, supplier responses, and customer/supplier quality signals in dashboard and management review
- CAPA 5 Why inline list columns for sequence, question, and answer

## Quality Gate Evidence

Release validation was executed from canonical `main` before tagging.

Automated checks:

- Python compile validation: PASS
- Manifest/XML validation: PASS
- Secret scan: PASS
- External-standard content safety scan: PASS
- Shell syntax validation: PASS
- Git diff whitespace validation: PASS
- Docker Compose configuration validation: PASS
- DEV install validation: PASS
- Existing DEV database upgrade validation: PASS

Odoo tests:

- Mission 16 regression: 110 post-tests, 0 failures, 0 errors

GitHub Actions:

- Workflow: `QMS CI`
- Run: `32550416651`
- Commit: `2c2fb856a07e3687b576c7f09bd02454eae6ef8f`
- Result: PASS

## Pilot Validation Evidence

Pilot database: `pmqms_oliva_pilot`

Backup created before pilot validation:

```text
/opt/perfect-match/backups/odoo-oliva-pilot/pmqms-oliva-pilot-20260822T041155Z.tar.gz
```

Pilot validation:

- Backup validation: PASS
- Pilot update: PASS
- Pilot HTTP health: 200
- Implementation controls: 37
- Generated activities/tasks: 74
- Required evidence requirements: 37
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
- QMS action/view smoke: PASS
- CAPA 5 Why inline columns: PASS

No fictional customer/supplier quality, people, or calibration demo data was seeded into the pilot.

## Release Limitations

- `v1.0.0-rc4` is a pre-release candidate and not the final stable `v1.0.0` release.
- The release does not add cost of quality, ERP bridges, licensing, customer portal production workflows, AI copilot, n8n ownership of QMS state, or new external standards.
- Readiness metrics reflect recorded implementation status only and do not constitute certification, certification-body approval, or a guarantee of compliance.
- GitHub Actions currently reports non-blocking Node.js runtime warnings for third-party actions and a Node runtime deprecation warning. This is tracked as technical debt.

## Versioning

Odoo addon manifest versions preserve the repository's module versioning strategy. RC4 is represented by the Git tag and GitHub pre-release:

```text
v1.0.0-rc4
```
