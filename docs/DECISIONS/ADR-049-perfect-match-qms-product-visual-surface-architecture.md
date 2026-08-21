# ADR-049: Perfect Match QMS Product Visual Surface Architecture

## Status

Accepted

## Context

Perfect Match QMS had a strong backend and a unified application shell, but Mission 13 required the product to visibly demonstrate the capabilities already implemented in the backend. The product owner should not need to inspect models, tests, or source code to understand what the system can do.

## Decision

Perfect Match QMS will use an Odoo-native product visual surface for current capabilities. The application will expose customer-facing routes through menus, actions, list views, form views, kanban views, stat buttons, search filters, Odoo-native decorations, statusbars, and concise empty states.

The implementation preserves the existing architecture:

- Odoo remains the application platform.
- Activities remain `project.task` records in a QMS context.
- The existing readiness engine remains authoritative.
- Historical readiness assessments remain immutable snapshots.
- Framework/admin methodology remains authorized for managers/admins.
- External mappings remain metadata only.
- No separate frontend framework is introduced for Mission 13.
- No optional demo addon is introduced in Mission 13.

## Consequences

The product is more demonstrable without adding hidden backend engines. Visual consistency is maintained with Odoo-native behavior and security boundaries. Future demo data can be added as a separate optional addon and disposable database, but production modules must not depend on it.

## Verification

Mission 13 verification includes XML/action validation, focused Odoo tests for visual route reachability, existing regression tests, pilot validation, and browser-based visual QA.
