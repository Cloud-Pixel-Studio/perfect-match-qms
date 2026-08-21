# PMQMS-057 - Perfect Match QMS v1.0.0-rc3 Release Candidate

Priority: HIGH
Project: PMQMS PLATFORM
Module: Odoo Architecture
Cycle: Backlog
Labels: odoo, testing, documentation, infrastructure, pilot, release
Dependencies: PMQMS-056

## Objective

Freeze and publish the Perfect Match QMS `v1.0.0-rc3` release candidate after the complete product visual surface, people/training/competency, and equipment/calibration product baseline.

## Description

Execute the formal RC3 release cut without adding new product scope. Validate canonical main, run the required quality gates, update and verify the Oliva pilot, prepare release documentation, create an annotated Git tag, publish a GitHub pre-release, and close Plane tracking only after the release is verifiably available.

## Acceptance Criteria

- Canonical `main` is clean, synchronized with `origin/main`, and contains the Mission 15 equipment/calibration merge.
- Historical `v1.0.0-rc1` and `v1.0.0-rc2` tags remain intact, and `v1.0.0-rc3` does not exist before the release cut.
- Python compile validation, addon manifest/XML validation, secret scan, content-safety scan, shell syntax validation, git diff check, DEV configuration validation, DEV upgrade validation, and the full Odoo regression suite pass.
- GitHub Actions on canonical main passes for the validated release source.
- The Oliva pilot backup, update, HTTP health check, data-integrity counts, and UI/action smoke checks pass without seeding fictional calibration demo data.
- RC3 release notes and baseline documentation are committed and linked from the documentation index.
- An annotated `v1.0.0-rc3` tag is created from validated `main` and pushed to the canonical GitHub repository.
- A GitHub pre-release named `Perfect Match QMS v1.0.0-rc3` is published without attaching backups, database dumps, filestore data, secrets, keys, credentials, or customer data.
- Plane is updated through the official Plane API/MCP only, and this work item is closed after final release verification passes.
