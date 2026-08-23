# ADR-056: Standalone Product Organization and Site Foundation

## Status

Accepted

## Context

Mission 18 required a standalone QMS product boundary and a real organization
and Site foundation for customer-facing configuration. Discovery found an
existing `pm.qms.organization` model but no canonical Site, facility, or plant
model. `res.company` already provides Odoo's technical multi-company boundary.

## Decision

Extend `pm.qms.organization` as the authoritative QMS operational company
profile and add `pm.qms.site` in `pm_qms_core`. Sites have organization-derived
company scope, unique organization-local codes, archive/history behavior, and
one active primary site per organization. Processes may reference multiple
sites; people and monitoring resources may each reference one primary/site
record. Site-specific record rules and commercial entitlement logic are outside
this decision.

Enforce the standalone boundary with a repository script that audits all addon
manifests and rejects functional ERP dependencies. Use Odoo ORM for Demo seed
and validation; do not modify PostgreSQL directly.

## Consequences

Customers can maintain a Company Profile and an extensible list of operational
Sites from QMS Configuration. Existing records remain compatible because site
scope is optional except for the organization relationship. Future site-aware
workflow and authorization decisions can build on one canonical model without
inventing a second company model or imposing a three-site limit.
