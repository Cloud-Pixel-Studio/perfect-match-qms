# GitHub Workflow

This repository uses GitHub as the source-code system of record for Perfect Match Digital QMS. GitHub stores source code, tests, documentation, CI configuration, and release metadata only. It is not a backup target for customer databases, filestore data, credentials, private attachments, or licensed standard publications.

## Default Flow

Use a small branch and pull request flow for normal work:

```text
main
  -> feature/*, fix/*, chore/*, or hotfix/*
  -> Pull Request
  -> GitHub Actions QMS CI
  -> Review
  -> Merge
  -> Release tag when needed
```

`main` represents the current reviewed product line. Feature branches should stay focused and should not mix product changes with infrastructure or release housekeeping.

## Branch Names

Use practical, searchable names:

- `feature/qms-objectives-dashboard`
- `fix/capa-effectiveness-state`
- `chore/github-foundation`
- `hotfix/oliva-pilot-restore-script`

Historical mission branches are preserved to keep the Mission 01-10 development record available. New work should branch from `main` unless a release manager explicitly chooses a maintenance branch.

## Pull Requests

Every non-trivial change should use a pull request into `main`. The pull request should explain the scope, list validation evidence, and call out migration, security, multi-company, or documentation impact.

Keep pull requests small enough to review. Avoid combining unrelated Odoo addon changes, infrastructure changes, and documentation cleanup unless they are required for the same outcome.

## Required Checks

The `QMS CI` workflow is the baseline gate. It is expected to cover:

- Python compilation for addons and deployment scripts.
- Odoo addon manifest and XML validation.
- Secret scanning.
- External-standard content safety scanning.
- Docker Compose validation for the development runtime.
- Mission regression tests when the workflow path supports them.

Do not weaken CI to make a pull request pass. If CI fails because of the GitHub environment or an external dependency, document the cause and fix the workflow safely.

## Security Rules

Never commit:

- real `.env` files or deployment credentials
- API tokens or passwords
- SSH keys, private keys, or certificates containing private material
- PostgreSQL dumps or database files
- Odoo filestore archives
- customer documents, evidence, exports, or attachments
- Oliva Torras backups, pilot data, or private files
- licensed standard publications or copied external-standard text

`.env.example` files are allowed only when they contain blank, local-only, or obvious placeholder values.

## Governance Boundary

GitHub Issues, Pull Requests, QMS CI, merge history, and releases are the sole
active engineering governance record. The repository `plane/` directory is a
read-only historical archive; do not synchronize it or call a Plane API.

## Releases

Release candidates use annotated tags. The first RC tag is:

- `v1.0.0-rc1`

GitHub Releases should use the matching release notes in `docs/` and be marked as prerelease until customer go-live is complete. Do not attach database backups, customer files, licensed standards, or environment files to releases.

## Backup Boundary

GitHub is the offsite source-code backup. It does not replace operational backups.

Operational backup scope remains separate:

- customer PostgreSQL databases
- Odoo filestores
- deployment configuration secrets
- private evidence files and attachments

Those belong in the encrypted offsite backup process, not in Git.

## Emergency Changes

Emergency fixes should use `hotfix/*` branches and still pass CI. If branch
protection allows an owner/admin bypass, reserve it for genuine emergency
recovery and document the reason in the GitHub Pull Request or release notes.
Force pushes to `main` remain prohibited.

## Local Validation

Before opening a pull request, run the relevant local checks when possible:
