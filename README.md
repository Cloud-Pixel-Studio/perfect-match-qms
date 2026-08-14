# Perfect Match Digital QMS

Perfect Match Digital QMS is a proprietary digital management system implementation platform for Perfect Match Investments LLC.

The product will help organizations implement, operate, monitor, and improve management systems through Perfect Match proprietary methods, controls, workflows, templates, evidence expectations, and implementation guidance.

## IP Boundary

This repository must not contain copyrighted ISO, IATF, AS, SAE, CMMC, or other third-party standard text unless a valid license explicitly permits it and use is authorized.

Perfect Match proprietary controls are stored separately from external standard references and mappings.

## Target Platform

- Odoo 19 Self-Hosted.
- Python and Odoo ORM.
- PostgreSQL.
- Odoo Owl, JavaScript, XML/QWeb.
- Docker, Docker Compose, Linux, Nginx, TLS.
- n8n for external integration automation.
- OpenAI API for controlled QMS assistance.
- Plane for project management.

## Current Status

Mission 02 established the Odoo DEV environment and the initial `pm_qms_core` addon scaffold.

Core paths:

- `deployment/docker/odoo-dev.compose.yml`
- `deployment/scripts/odoo-dev.sh`
- `docs/DEV_ENVIRONMENT.md`
- `docs/TESTING.md`
- `addons/pm_qms_core/`

## DEV Quick Start

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh init-secrets
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh test-core
```
