# Perfect Match QMS Application Shell

Perfect Match QMS is a product experience built on Odoo 19. The backend stays
modular, but users should enter one customer-facing application: `Perfect Match
QMS`.

## Purpose

Mission 11 introduced `pm_qms_app` as a thin application shell addon. It does
not replace the existing QMS modules and it does not duplicate Odoo Project.
Its responsibility is to make the existing QMS platform feel like one product:

- product branding and app launcher identity;
- dashboard/home action;
- unified navigation;
- implementation-centered entry points;
- role-aware menu visibility.

Technical addons continue to own domain models and business rules. The shell
only organizes and exposes them.

## Odoo 19 App Behavior Findings

Odoo 19 distinguishes between module catalog entries and application launcher
menus:

- `ir.module.module.application` controls whether an addon is treated as an
  application in the Apps catalog.
- root `ir.ui.menu` records with no parent are the application entries loaded
  by the web client launcher.
- `ir.ui.menu.web_icon` supplies the icon metadata for the launcher entry.
- `ir.ui.menu.load_menus()` assigns the active app context from the root menu,
  not from the technical addon that owns every downstream model.

Before Mission 11, `pm_qms_core` had `application=True` and appeared as
`Perfect Match QMS Core`. After Mission 11, `pm_qms_app` is the product
application and `pm_qms_core` is a technical service addon.

## Addon Responsibilities

`pm_qms_app`:

- has manifest name `Perfect Match QMS`;
- has `application=True`;
- depends on the complete implemented QMS stack through Mission 11;
- defines the dashboard transient model `pm.qms.dashboard`;
- installs dashboard, navigation, and implementation UX view updates;
- updates the existing root menu branding and default action.

`pm_qms_core`:

- keeps foundational models, security groups, and the historical root menu XML
  ID;
- has `application=False`;
- is named `Perfect Match QMS Core Services` to avoid presenting it as the
  commercial product.

The root menu XML ID remains `pm_qms_core.menu_pm_qms_root` because downstream
addons already depend on that root. The shell updates that record rather than
creating a competing root menu, avoiding circular dependencies and duplicate
application entries.

## Navigation Architecture

The target navigation is one product tree under `Perfect Match QMS`:

```text
Perfect Match QMS
|-- Dashboard
|-- Implementations
|   |-- New Implementation
|   |-- Implementations
|   |-- Controls
|   |-- Activities
|   `-- Readiness Assessments
|-- Documents
|-- Evidence
|-- Risk & Improvement
|   |-- Risks & Opportunities
|   |-- NCR
|   `-- CAPA
|-- Audit
|   |-- Audit Programs
|   |-- Audits
|   |-- Findings
|   `-- Audit Evidence
|-- Performance
|   |-- Quality Objectives
|   |-- KPIs
|   |-- KPI Measurements
|   |-- Customer Performance
|   `-- Supplier Performance
|-- Management Review
|-- Framework
|   |-- Framework Controls
|   |-- Packs
|   |-- Framework Activities
|   |-- Evidence Requirements
|   `-- External Mappings
`-- Configuration
    |-- Organizations
    |-- Processes
    `-- Administration / Migration
```

The shell reuses existing menus and actions wherever possible. It renames and
reorders the implementation project and task entries so users see
`Implementations` and `Activities` rather than being pushed into generic Odoo
Project first.

## Dashboard Architecture

The dashboard uses a native Odoo transient model and form view. No custom Owl
client was added for the first product shell because the required behavior is
server-side aggregation, standard actions, and simple navigation.

Model:

```text
pm.qms.dashboard
```

Primary context fields:

- `organization_id`
- `implementation_project_id`

Data sources:

- implementation readiness: `pm.qms.implementation.project` computed metrics;
- controls: `pm.qms.implementation.control`;
- activities: generated `project.task` records linked by QMS fields;
- evidence: implementation evidence counters;
- QMS health: risk, NCR, CAPA, and audit finding models;
- performance: objectives, KPIs, customer performance, and supplier
  performance;
- management review: review and review action models.

Dashboard readiness is live. Historical readiness assessments remain immutable
snapshots and are not reused as the live dashboard formula.

## Organization Context Rules

The dashboard never blindly aggregates unrelated organizations. It searches
organizations inside the user's allowed companies and exposes an organization
selector. If multiple accessible organizations exist, the selector makes the
context explicit.

Counters are scoped by:

- selected organization;
- selected organization company;
- current user's allowed companies;
- normal Odoo ACLs and record rules.

The dashboard does not use `sudo()` to make counts appear. If a user cannot see
records through Odoo security, those records are not counted for that user.

## Project Abstraction

Mission 11 keeps the proven Odoo-native implementation strategy:

```text
QMS Implementation -> project.project
QMS Activity       -> project.task
```

The customer-facing UX uses `Implementations` and `Activities`, while the data
still lives in Odoo Project where appropriate. Smart buttons on implementation
records open filtered controls, activities, evidence, and readiness assessment
views without requiring the user to start from the generic Project app.

## Security And Menu Visibility

Existing groups remain authoritative:

- `QMS User`
- `QMS Manager`
- `QMS Administrator`

Mission 11 uses menu visibility for product ergonomics, not as the only
security layer. ACLs and record rules still control data access.

Framework and external mapping menus are manager/admin areas because reusable
methodology should not be edited accidentally by normal implementation users.
Migration tools are placed under administration-style navigation and restricted
to QMS administrators.

## 74 vs 72 Task Investigation

The Oliva pilot Quality Pack has:

- 37 pack controls;
- 74 active reusable framework activities;
- 37 implementation controls;
- 74 expected generated activity pairs;
- 74 generated `project.task` records;
- 0 archived generated tasks;
- 0 missing generated activity pairs;
- 0 extra generated activity pairs.

The observed `72 Tasks` on the native Odoo Project card is not a generator bug.
Odoo 19's Project kanban card displays `open_task_count`, not total task count.
In the pilot, two generated tasks were already closed:

- `Identify context inputs`
- `Review context changes`

Therefore:

```text
framework activities:          74
generated QMS tasks:           74
Odoo project task_count:       74
Odoo project open_task_count:  72
Odoo project closed_task_count: 2
```

No duplicate tasks should be created to force the Project card to display 74.
The QMS dashboard and implementation metrics should explain total, open, and
completed activities separately.
