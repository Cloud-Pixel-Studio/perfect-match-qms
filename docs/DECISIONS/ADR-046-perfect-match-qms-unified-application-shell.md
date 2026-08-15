# ADR-046: Perfect Match QMS Unified Application Shell

## Status

Accepted

## Context

Perfect Match QMS had matured as a set of modular Odoo addons, but the Odoo app
launcher exposed the technical core addon as `Perfect Match QMS Core`. That
made the product feel like an implementation detail rather than a unified QMS
application.

The existing backend is intentionally modular and should not be collapsed into
one large addon. The implementation engine also intentionally uses native Odoo
Project models:

```text
Implementation -> project.project
Activity       -> project.task
```

Mission 11 needed a product shell without replacing Odoo, duplicating Project,
or creating circular dependencies between core and downstream modules.

## Decision

Create `pm_qms_app` as a thin customer-facing application shell addon.

`pm_qms_app` is responsible for:

- product name and application metadata;
- app launcher icon;
- dashboard/home action;
- unified QMS navigation;
- implementation-centered actions and smart buttons;
- role-aware menu organization.

`pm_qms_app` depends on the implemented QMS stack through Mission 11 and has
`application=True`.

`pm_qms_core` remains the foundational services addon, but has
`application=False` and is no longer presented as the primary customer-facing
product.

The existing root menu XML ID, `pm_qms_core.menu_pm_qms_root`, remains the root
application menu because downstream addons already attach to it. The shell
updates that root menu's visible product name, icon, sequence, and default
dashboard action instead of creating a duplicate root menu.

The dashboard is implemented as a native Odoo transient model and form view for
the first product shell. It queries real operational data through Odoo ORM and
uses existing computed readiness metrics rather than adding a second readiness
formula.

## Security

The dashboard and actions use normal ORM access. They do not use `sudo()` for
cross-organization counters. Menu visibility improves navigation, but ACLs and
record rules remain authoritative.

Framework and external mapping menus are manager/admin areas. Migration tooling
is restricted to QMS administrators.

## Consequences

Users now see `Perfect Match QMS` as the product entry point rather than
`Perfect Match QMS Core`.

Technical addons remain independently testable and maintainable. The shell can
evolve product UX without moving business rules out of the domain addons.

The root menu remains technically defined by `pm_qms_core`, but its visible
behavior is owned by the application shell. This preserves compatibility while
avoiding circular dependencies.

Odoo Project remains available underneath the implementation engine. Users can
operate QMS implementations through Perfect Match navigation without starting
from the generic Project app.

Future front-end work may add Owl components if the dashboard requires richer
interaction, but the first version stays server-side and native because it is
mostly aggregation and action routing.
