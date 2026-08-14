# Changelog

## 0.1.0 - 2026-08-14

- Added isolated Odoo 19 DEV Docker Compose stack with PostgreSQL 15 under `deployment/docker/dev/`.
- Added `deployment/scripts/odoo-dev.sh` for secrets, config validation, startup, install, and tests.
- Generated DEV runtime secrets outside Git under `/opt/perfect-match/secrets/odoo-dev/`.
- Scaffolded `pm_qms_core` as the first Odoo addon.
- Added QMS organization, process, proprietary control, implementation activity, evidence requirement, and external mapping models.
- Added QMS User, QMS Manager, and QMS Administrator groups with access rights and company-boundary record rules.
- Added sequence data, menus, native Odoo views, and post-install tests.
- Added DEV environment, architecture, testing documentation, and ADR-010.
- Validated `pm_qms_core` install and tests on Odoo 19.

## 0.0.1 - 2026-08-14

- Created engineering repository structure.
- Added agent instructions and planning framework.
- Added product, architecture, security, deployment, workflow, and IP policy documentation.
- Added initial ADRs.
- Added Plane project-management source files.
- Added initial 52-item engineering backlog.
- Added placeholder Odoo addon, standard pack, framework, deployment, and test directories.
