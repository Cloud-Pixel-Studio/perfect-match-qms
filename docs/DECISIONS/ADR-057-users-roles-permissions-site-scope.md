# ADR-057: Users, Roles, Permissions, and Site Scope

## Status

Accepted for Mission 19.

## Context

The standalone QMS already had company-boundary rules and compatibility groups,
but Demo personas all inherited manager and administrator access. Customer
users need explicit product roles and server-side organization/site/process
scope without a custom ACL builder or a second identity model.

## Decision

Use Odoo `res.groups` for a fixed product role catalog and extend `res.users`
with explicit QMS organization, site, and process scope. Add global scope record
rules so scope is ANDed with existing company rules. Keep `pm.qms.person.user_id`
as the identity link. Keep the existing `pm.qms.role` model for competency and
responsibility metadata only.

The product UI is `Perfect Match QMS > Configuration > Users & Access`. It
exposes the approved role allow-list and scope fields, not technical groups,
ACLs, record rules, or licensing controls.

## Consequences

The model is easy to test with `with_user`, fail-closed by default, and remains
inside the Odoo monolith. Demo seed assignments are deterministic. Existing
workflow actions remain the authority for approval and closure. Adding a new
role requires a code and security review rather than a runtime role designer.
