# Release Baseline v1.0.0-rc2

Release: `v1.0.0-rc2`

Release date: 2026-08-21

Release type: Product Experience and Guided Implementation release candidate

## Baseline Source

Validated canonical main before release documentation:

```text
5b2c14cfec6e1d0434fa273b8ded1e6a0444b134
```

The authoritative RC2 source is the pushed annotated Git tag `v1.0.0-rc2` in the canonical GitHub repository. The final tag target is verified at release time and reported in the release evidence.

Canonical repository:

```text
https://github.com/Cloud-Pixel-Studio/perfect-match-qms
```

## Product Scope

RC2 freezes the reusable Perfect Match QMS baseline containing:

- Application shell and unified navigation
- Executive dashboard
- Guided implementation projects
- Framework-pack implementation areas
- Proprietary Perfect Match control guidance
- Controls, activities, evidence, gaps, and readiness center
- Deterministic recommended actions
- Activity UX backed by Odoo `project.task`
- Native Odoo Project preserved for authorized users
- Documents, evidence, risk, NCR, CAPA, audit, objectives, KPI, performance, and management review modules
- Versioned framework packs and implementation generator
- Existing migration tooling

## Quality Gate Evidence

Release validation was executed from canonical `main` before tagging.

Automated checks:

- Python compile validation: PASS
- Manifest/XML validation: PASS
- Secret scan: PASS
- External-standard content safety scan: PASS
- Shell syntax validation: PASS
- Git diff whitespace validation: PASS
- Existing DEV database upgrade validation: PASS

Odoo tests:

- Mission 11: 86 post-tests, 0 failures, 0 errors
- Mission 12: 86 post-tests, 0 failures, 0 errors
- Mission 12.1: 86 post-tests, 0 failures, 0 errors

GitHub Actions:

- Workflow: `QMS CI`
- Run: `32486931970`
- Commit: `5b2c14cfec6e1d0434fa273b8ded1e6a0444b134`
- Result: PASS

## Pilot Validation Evidence

Pilot database: `pmqms_oliva_pilot`

Backup created before pilot validation:
