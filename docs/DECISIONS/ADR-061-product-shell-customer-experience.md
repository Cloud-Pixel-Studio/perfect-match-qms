# ADR-061: Product Shell and Customer Experience Boundary

- Status: Accepted
- Date: 2026-08-23
- Scope: Mission 22

## Context

Customers should experience Perfect Match QMS as the product while Odoo
remains the replaceable application runtime. The default Odoo root surface
exposed unrelated technical and ERP navigation to ordinary QMS users.

## Decision

Extend `pm_qms_app` as the single product-shell boundary. Use supported Odoo
addon inheritance, QWeb templates, assets, menu groups, and existing QMS
security groups. Reserve generic platform roots for `base.group_system`, keep
QMS configuration under the Perfect Match root, and separate the technical
Demo administrator from the seeded Quality Manager persona.

## Consequences

The customer path is clearer and the technical runtime remains upgradeable.
Menu visibility is improved without pretending that menus are authorization;
ACLs, record rules, and action security remain authoritative. The shell does
not add a second permission engine, unrelated ERP dependencies, a custom
frontend rewrite, or an Odoo core fork.

## Rejected alternatives

- CSS-only hiding of technical menus.
- Installing unrelated ERP applications only to hide their roots.
- A separate branding addon duplicating `pm_qms_app`.
- Modifying Odoo core templates or source files.
