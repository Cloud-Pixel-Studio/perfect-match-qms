# AGENTS.md

Permanent instructions for Codex and future engineering agents.

## Product

This repository contains Perfect Match Digital QMS.

## Architecture

Odoo must remain the application platform. Do not replace Odoo with another framework without an explicit Architecture Decision Record and user authorization.

## Development

Prefer modular Odoo addons, clean Python, Odoo ORM, PostgreSQL, Owl where custom frontend components are necessary, and standard Odoo functionality before custom development.

## Intellectual Property

Never copy or reconstruct copyrighted ISO, IATF, SAE, AS, CMMC, or other standards. Perfect Match controls must use proprietary wording. External mappings must remain separate and limited to standard name and clause/reference identifiers.

## Security

Never commit passwords, tokens, API keys, private keys, production credentials, or secret connection strings. Use environment variables, excluded secret files, or an approved secrets-management mechanism.

## Data

Never modify production databases directly unless specifically authorized. Use application APIs, Odoo ORM, migrations, or documented import/export mechanisms. Never modify Plane's PostgreSQL database directly for project setup.

## Git

Every meaningful feature should correspond to a tracked Plane work item. Use feature branches when GitHub integration is activated later.

## Testing

New functionality must include appropriate automated tests. Never declare a feature complete merely because code was written.

## Documentation

Architectural decisions must be documented. Update documentation when architecture changes.
