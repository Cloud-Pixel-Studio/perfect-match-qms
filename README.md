# Perfect Match QMS

## Overview

Perfect Match QMS is a digital quality management system platform for helping
organizations implement, operate, measure, audit, improve, and assess the
readiness of their management system. It combines Perfect Match proprietary
methodology, workflows, controls, implementation guidance, and evidence
expectations in one product.

The current application runtime is self-hosted Odoo 19. Odoo provides the
runtime, authentication, ORM, workflow and access-control foundations; Perfect
Match QMS owns the product modules, domain behavior, and customer experience.

The product is proprietary to Perfect Match Investments LLC. It is not an Odoo
fork, a theme, or a generic collection of unrelated Odoo modules.

## Current Product Capabilities

The current customer module set provides:

- Guided QMS implementation projects, activities, control instances, and
  readiness assessments.
- Controlled documents, revisions, evidence requirements, and evidence review.
- Risks and opportunities, nonconformities, CAPA, and corrective-action
  effectiveness workflows.
- Internal audit programs, audits, criteria, evidence, findings, and controlled
  finding-to-NCR integration.
- Objectives, KPIs, historical measurements, customer performance, and supplier
  quality evaluation.
- Management Review records with historical input snapshots and follow-up
  actions.
- People, training, competency, equipment, calibration, and impact assessment.
- Customer quality, supplier quality, Cost of Quality, and the unified Action
  Center.
- Organizations, Sites, Processes, scoped access, and customer user roles.
- The Perfect Match customer shell, product navigation, dashboard, and
  commercial licensing.

The ordered customer module manifest is maintained in
[`deployment/customer/modules.txt`](deployment/customer/modules.txt). Historical
pilot material is retained for traceability but is not current product data.

## Supported Standards

The generic Perfect Match QMS foundation and its operational modules are
standard-neutral. Standard profiles are separate Perfect Match addons.

The only currently supported standard profile is **ISO 9001**, implemented by
[`pm_qms_iso9001`](addons/pm_qms_iso9001/). Its dependency direction is:

```text
pm_qms_iso9001
        |
        v
Perfect Match generic QMS and methodology foundation
```

The generic foundation does not depend on ISO 9001. The ISO addon owns its
profile metadata, reference identifiers, review workflow, and customer
navigation. An operational Perfect Match control can be related to approved
reference metadata without duplicating customer QMS records or external
standard text.

## Architecture

Perfect Match QMS is a modular Odoo monolith composed of Python/Odoo ORM
services, PostgreSQL persistence, Owl/JavaScript, XML/QWeb views, and SCSS
assets. Docker Compose provides the local DEV and product Demo runtimes. Nginx
and TLS provide the applicable reverse-proxy boundary.

Business and domain behavior belongs in Perfect Match addons and services.
The product uses supported Odoo extension mechanisms and does not modify or
fork Odoo core.

## Customer Deployment Model

Each customer production deployment is isolated and has its own:

- database and Odoo filestore;
- environment identity and signed license;
- secrets and runtime configuration; and
- backup archives and recovery metadata.

Customer instances are created from approved Perfect Match release bundles.
They do not run from live `main`, and commercial tenancy is not based on one
shared unrestricted multi-company database. Customer deployment, upgrade,
backup, and recovery procedures are documented in
[`docs/CUSTOMER_DEPLOYMENT_ARCHITECTURE.md`](docs/CUSTOMER_DEPLOYMENT_ARCHITECTURE.md),
[`docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md`](docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md),
and [`docs/CUSTOMER_UPGRADE_RUNBOOK.md`](docs/CUSTOMER_UPGRADE_RUNBOOK.md).

## Licensing

Perfect Match QMS uses signed offline licenses with environment binding and
capacity entitlements for companies, Sites, and named QMS users. Verification
is local to the installation; the product does not require permanent
phone-home or continuous Internet verification.

Licensing is separate from Odoo ACLs and record rules. A license controls
commercial entitlement, while Odoo remains the system of record for identity,
permissions, workflows, and QMS data. See
[`docs/LICENSING_ARCHITECTURE.md`](docs/LICENSING_ARCHITECTURE.md) and
[`docs/COMMERCIAL_ENTITLEMENTS.md`](docs/COMMERCIAL_ENTITLEMENTS.md) for the
design boundary.

## Security and Access

Access is role-based and combines Odoo ACLs, record rules, workflow authority,
and Site/Process/organization scope. The model supports segregation of duties
between operational QMS work and platform administration.

Menu visibility is a usability layer, not a security boundary. Permissions and
server-side access checks remain authoritative. Technical administrators retain
the platform administration surfaces required to maintain an installation;
normal QMS users receive only the customer-facing QMS experience appropriate to
their role and scope.

## Product Shell

Normal QMS users enter the Perfect Match QMS product shell, with grouped
navigation for Dashboard, Implementation, Quality Operations, Assurance,
Performance, Action Center, Standards, and Configuration. The shell organizes
existing QMS actions without replacing their domain ownership.

Technical administrators retain the underlying Odoo Apps, Settings,
maintenance, and troubleshooting capabilities needed to operate the platform.
The shell and its boundaries are described in
[`docs/PRODUCT_SHELL_ARCHITECTURE.md`](docs/PRODUCT_SHELL_ARCHITECTURE.md) and
[`docs/NAVIGATION_ARCHITECTURE.md`](docs/NAVIGATION_ARCHITECTURE.md).

## Development Quick Start

The supported local DEV loop is:

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh init-secrets
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh install-mission23
./deployment/scripts/odoo-dev.sh health
./deployment/scripts/odoo-dev.sh test-mission23
```

The DEV database is `pmqms_dev`; runtime secrets are generated outside Git.
Open the local service through the documented SSH tunnel or the configured
local binding. See [`docs/DEV_ENVIRONMENT.md`](docs/DEV_ENVIRONMENT.md),
[`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md), and
[`docs/TESTING.md`](docs/TESTING.md) for focused update and test procedures.

## Repository Structure

```text
addons/
  pm_qms_core/             generic organizations, processes, controls, evidence
  pm_qms_app/              product shell, dashboard, branding, navigation
  pm_qms_implementation/   projects, activities, and readiness
  pm_qms_pack_quality/     Perfect Match proprietary quality methodology pack
  pm_qms_iso9001/          ISO 9001 standard profile addon
  pm_qms_license/          commercial licensing and entitlements
  pm_qms_*                 operational QMS domains
deployment/
  customer/                approved customer module manifest and tooling
  docker/                  DEV and Demo Compose definitions
  scripts/                 supported validation and environment helpers
docs/
  architecture, security, deployment, licensing, testing, and runbooks
framework/
  approved metadata and reference-mapping examples
.github/
  CI workflows and repository quality gates
```

## Validation and Release Model

`main` is the development and integration branch. Customer deployments come
from approved release bundles, with controlled preflight, backup, update,
health, and manifest procedures. Historical release tags are immutable.

Odoo major-version upgrades are controlled engineering and customer migration
events; they are not automatic customer upgrades. Repeatable validation commands
and release evidence are documented in [`docs/TESTING.md`](docs/TESTING.md),
[`docs/CI.md`](docs/CI.md), and the release runbooks.

## Intellectual Property Boundary

The repository does not contain copied ISO or other third-party standard
requirement text unless separately authorized. Standard names, editions,
publishers, clause/reference identifiers, and mapping metadata may be stored
where appropriate. Perfect Match proprietary methodology and controls remain
separate from third-party publications.

Users remain responsible for obtaining authorized official standards where
required. See [`docs/IP_AND_STANDARDS_POLICY.md`](docs/IP_AND_STANDARDS_POLICY.md)
and [`docs/STANDARD_ADDON_ARCHITECTURE.md`](docs/STANDARD_ADDON_ARCHITECTURE.md).

## Compliance and Certification Notice

Perfect Match QMS supports QMS implementation and operation, readiness
assessment, evidence organization, and internal quality processes. It does not
guarantee certification or compliance, replace a certification body, or replace
authorized access to official standards.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - product architecture and
  domain relationships.
- [`docs/APPLICATION_SHELL.md`](docs/APPLICATION_SHELL.md) - application shell
  responsibilities and navigation.
- [`docs/DEMO_ENVIRONMENT.md`](docs/DEMO_ENVIRONMENT.md) - fictional Demo
  environment and supported validation commands.
- [`docs/SECURITY.md`](docs/SECURITY.md) - security principles and boundaries.
- [`docs/index.md`](docs/index.md) - documentation index.
