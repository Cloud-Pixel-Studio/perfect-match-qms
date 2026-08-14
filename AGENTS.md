# AGENTS.md

Permanent instructions for Codex and future engineering agents.

Codex reads `AGENTS.md` files hierarchically. The root file applies to the whole repository. More specific `AGENTS.md` files inside subdirectories override or extend these instructions for that subtree.

## Product

This repository contains Perfect Match Digital QMS.

## Architecture

Odoo must remain the application platform. Do not replace Odoo with another framework without an explicit Architecture Decision Record and user authorization.

Prefer a modular Odoo monolith first. Core QMS state and business rules belong in Odoo. n8n is for external automation and integration, not for owning QMS lifecycle state.

## Development

Prefer modular Odoo addons, clean Python, Odoo ORM, PostgreSQL, Owl where custom frontend components are necessary, and standard Odoo functionality before custom development.

Every meaningful feature should correspond to a tracked Plane work item.

## Intellectual Property

Never copy or reconstruct copyrighted ISO, IATF, SAE, AS, CMMC, or other standards. Perfect Match controls must use proprietary wording. External mappings must remain separate and limited to standard name and clause/reference identifiers.

## Security

Never commit passwords, tokens, API keys, private keys, production credentials, database dumps, TLS private keys, or secret connection strings.

Use environment variables, excluded secret files, Docker secrets, or an approved secrets-management mechanism.

## Plane

Plane is the project-management system of record.

Do not modify Plane PostgreSQL directly to create, update, close, delete, or repair workspaces, projects, cycles, modules, milestones, labels, or work items.

Use supported Plane mechanisms only, in this order:

1. Plane Compose or another supported Plane configuration mechanism, if available for the installed edition/version.
2. Official Plane REST API.
3. Official Plane MCP integration, if enabled and appropriate.

For a self-hosted Plane instance, configure credentials outside Git through:

- `PLANE_API_KEY`
- `PLANE_WORKSPACE_SLUG`
- `PLANE_BASE_URL`

`PLANE_API_TOKEN` may be supported as a backward-compatible alias only. Prefer `PLANE_API_KEY` in new automation.

Before creating Plane records, list existing records and match by stable name/identifier to avoid duplicates.

## Data

Never modify production databases directly unless specifically authorized. Use application APIs, Odoo ORM, migrations, or documented import/export mechanisms.

## Git

Use feature branches when GitHub integration is activated later. Keep commits focused and include verification notes in the final report.

## Testing

New functionality must include appropriate automated tests. Never declare a feature complete merely because code was written.

For Odoo addons, verify install/update and run focused Odoo tests before closing the related Plane work item.

## Documentation

Architectural decisions must be documented. Update documentation when architecture, security, data model, deployment, or workflow behavior changes.
