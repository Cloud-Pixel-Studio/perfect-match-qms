# ADR-062: Standard Add-on Architecture and ISO 9001 Separation

Status: Accepted

## Context

Perfect Match QMS is an Odoo modular monolith. The reusable QMS core, the
implementation/readiness engines, and the proprietary PM-QMS-QUALITY pack are
useful without a standards add-on. A standard reference profile must not make
that generic foundation appear to reproduce or contain an external standard.

## Decision

Use one Perfect Match add-on per management-system standard. Mission 23
implements only `pm_qms_iso9001`, which depends on the neutral
`pm_qms_pack_quality` pack. The add-on owns ISO 9001 profile metadata, the
customer-facing Standards navigation, and future approved reference mappings.
The base/core addons own generic controls, activities, evidence, framework
packs, mapping infrastructure, implementation generation, and readiness.

The current profile is adopted by stable code `PM-QMS-QUALITY-ISO9001` and
edition `2015`; installation is idempotent and refuses an unexpected edition
collision. Existing controls and operational records are not deleted or
recreated. No approved mappings are seeded.

Framework master data remains an administrator-only configuration surface.
Normal QMS roles consume generated implementation and operational records.

## Legal and product boundary

The product stores only standard name, edition, publisher, reference
identifiers, review state, and Perfect Match-authored notes. It does not copy
ISO requirement text, guidance, or copyrighted tables. ISO 14001, ISO 45001,
AS9100, AS9120, IATF 16949, and other standards are not implemented or shown
as unfinished menus.

## Consequences

The zero-standard installation remains valid and the ISO-enabled bundle adds
only ISO 9001. Future standards can be delivered as independent add-ons with
their own dependency and entitlement decisions without changing generic QMS
models. Current commercial licensing continues to govern environment,
company, Site, and named-user capacity; no standard-feature entitlement is
introduced by this mission.
