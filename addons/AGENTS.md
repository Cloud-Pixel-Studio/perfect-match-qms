# AGENTS.md

Instructions for Odoo addons under `addons/`.

## Platform

All code here must be valid Odoo 19 addon code unless an ADR explicitly authorizes another target.

Use Odoo ORM, model constraints, access rights, record rules, and migration patterns instead of direct database manipulation.

## Addon Boundaries

Keep addons modular:

- `pm_qms_core` owns shared QMS entities and lifecycle foundations.
- Domain addons should depend on `pm_qms_core` when they need core processes, controls, evidence, or mappings.
- Do not create circular dependencies.
- Prefer native Odoo behavior before custom code.

## Security

Every persisted model needs intentional access control. Add ACLs and record rules before considering an addon installable.

Respect company/client boundaries. Do not expose cross-company data unless the requirement and security model explicitly authorize it.

## Testing

New models and workflows need Odoo tests covering creation, permissions-sensitive relationships, constraints, state transitions, and IP boundary behavior.

Run focused tests from the repository root:

```bash
./deployment/scripts/odoo-dev.sh test-core
```

Add new script targets as additional addons become testable.

## Intellectual Property

Do not add external standard text to Python, XML, CSV, tests, demo data, comments, or docs. Store only external framework names and reference identifiers where mappings are required.
