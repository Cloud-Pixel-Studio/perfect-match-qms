# Release Baseline v1.0.0-rc3

Release: `v1.0.0-rc3`

Release date: 2026-08-21

Release type: Operational QMS expansion release candidate

## Baseline Source

Validated canonical main before release documentation:

```text
5cb9dc2d029988fdde9d46883bf89a3e660f8a51
```

The authoritative RC3 source is the pushed annotated Git tag `v1.0.0-rc3` in the canonical GitHub repository. The final tag target is verified at release time and reported in the release evidence.

Canonical repository:

```text
https://github.com/Cloud-Pixel-Studio/perfect-match-qms
```

## Product Scope

RC3 freezes the reusable Perfect Match QMS baseline containing:

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
- Existing DEV database upgrade validation: PASS

Odoo tests:

- Mission 15 regression: 103 post-tests, 0 failures, 0 errors

GitHub Actions:

- Workflow: `QMS CI`
- Run: `32530039351`
- Commit: `5cb9dc2d029988fdde9d46883bf89a3e660f8a51`
- Result: PASS

## Pilot Validation Evidence

Pilot database: `pmqms_oliva_pilot`

Backup created before pilot validation:

```text
/opt/perfect-match/backups/odoo-oliva-pilot/pmqms-oliva-pilot-20260821T224528Z.tar.gz
```

Pilot validation:

- Backup validation: PASS
- Pilot update: PASS
- Pilot HTTP health: 200
- Implementation areas: 6
- Implementation controls: 37
- Generated activities/tasks: 74
- Required evidence requirements: 37
- People records: 0
- Calibration equipment: 0
- Calibration events: 0
- Calibration impact assessments: 0
- Documents: 1
- Risks: 1
- NCR: 1
- CAPA: 1
- Audits: 1
- Management reviews: 1

No fictional calibration demo data was seeded into the pilot.

## Release Limitations

- `v1.0.0-rc3` is a pre-release candidate and not the final stable `v1.0.0` release.
- The release does not add customer complaints, 8D, SCAR, cost of quality, ERP bridges, licensing, customer portal, AI copilot, n8n, or new external standards.
- Readiness metrics reflect recorded implementation status only and do not constitute certification, certification-body approval, or a guarantee of compliance.
- GitHub Actions currently reports a non-blocking Node.js runtime deprecation warning for third-party actions. This is tracked as technical debt.

## Versioning

Odoo addon manifest versions preserve the repository's module versioning strategy. RC3 is represented by the Git tag and GitHub pre-release:

```text
v1.0.0-rc3
```
