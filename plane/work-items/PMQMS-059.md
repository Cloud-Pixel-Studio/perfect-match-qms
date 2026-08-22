# PMQMS-059 - Perfect Match QMS v1.0.0-rc4 Release Candidate

Priority: HIGH
Project: PMQMS PLATFORM
Module: Odoo Architecture
Cycle: Backlog
Labels: odoo, documentation, testing, infrastructure, pilot, technical-debt
Dependencies: PMQMS-058

## Objective

Cut and publish the Perfect Match QMS `v1.0.0-rc4` release candidate after validating the Mission 16 customer and supplier quality baseline.

## Description

Prepare release notes and baseline documentation, validate local and GitHub quality gates, validate the Oliva Torras pilot as a validation-only environment, preserve existing release tags, create an annotated `v1.0.0-rc4` tag, publish the GitHub pre-release, and close the release work item through supported Plane APIs.

## Acceptance Criteria

- `main` is synchronized with `origin/main` before release work starts.
- Existing tags `v1.0.0-rc1`, `v1.0.0-rc2`, and `v1.0.0-rc3` remain unchanged.
- Local validation passes for compile, addon validation, secret scan, content safety, shell syntax, diff whitespace, DEV install, DEV upgrade, and the Mission 16 regression suite.
- GitHub Actions `QMS CI` passes on the canonical release commit.
- Pilot backup, update, health, counts, action/view smoke, and CAPA 5 Why inline list validation pass.
- `docs/RELEASE_NOTES_v1.0.0-rc4.md`, `docs/RELEASE_BASELINE_v1.0.0-rc4.md`, `CHANGELOG.md`, and `docs/index.md` are updated.
- Annotated tag `v1.0.0-rc4` is pushed to GitHub and points to the final validated main commit containing release documentation.
- GitHub Release for `v1.0.0-rc4` is published as a pre-release and not as a draft.
- Plane work item is updated to DONE after publication using official Plane API or supported integration only.
