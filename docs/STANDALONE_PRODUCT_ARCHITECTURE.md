# Standalone Product Architecture

## Mission 18 Boundary

Perfect Match Digital QMS is a standalone Odoo product. Odoo remains the
application platform, QMS lifecycle state remains in the Perfect Match addons,
and GitHub is the engineering and work-management system of record.
This foundation does not implement licensing, commercial limits, full RBAC,
ERP bridges, or Mission 19 scope.

## Architecture Discovery

- The authoritative operational QMS company model is the existing
  `pm.qms.organization` record.
- `res.company` remains Odoo's technical and multi-company boundary. It is not
  a subscription, entitlement, or site-limit mechanism.
- Before Mission 18 there was no canonical QMS Site, facility, location, or
  plant model. The previous Demo metadata key was replaced by real Site records.
- Existing organization, process, people, and equipment records retain their
  existing models. No duplicate organization/company model was introduced.
- Sites live in `pm.qms.site` in `pm_qms_core`, linked to exactly one QMS
  organization and its derived technical company.

## Organization and Company Profile

`pm.qms.organization` now carries the QMS scope, primary quality contact, and
one-to-many Site relationship. The customer-facing menu is:

`Perfect Match QMS > Configuration > Company Profile`

The organization record is the operational profile for one QMS customer or
business unit. The Odoo company supplies technical isolation and standard
company contact context; it does not grant product entitlements.

## Site Foundation

`pm.qms.site` provides a stable code and name, organization, derived company,
site type, optional address/contact, timezone, phone, email, site manager,
primary/headquarters flag, description, notes, and archive state.

Invariants:

- Site organization is required and determines the technical company.
- Site codes are unique within an organization.
- A linked address/contact and manager must align to the organization's company.
- One active primary/headquarters site is allowed per organization.
- Sites are archived for history; active sites cannot be deleted.
- Archived sites referenced by processes or monitoring resources cannot be
  deleted.
- There is no artificial three-site limit.

The customer-facing menu is:

`Perfect Match QMS > Configuration > Sites`

## Minimum Site Propagation

| Model | Scope | Mission 18 decision |
| --- | --- | --- |
| Organization | One organization to many sites | Implemented |
| Process | Optional many applicable sites | Implemented |
| Person | Optional primary site | Implemented |
| Equipment | Optional site | Implemented |
| Documents, risks, NCR, CAPA, audit, KPI, customer/supplier quality | Existing organization/company scope | Deferred until a specific workflow proves site scope is needed |
| Record rules by site | None | Deferred to Mission 19 |

Cross-organization and cross-company validation is enforced on the propagated
relationships. The product does not infer a site from a commercial plan.

## Standalone Dependency Boundary

Every addon manifest is checked by
`deployment/scripts/standalone-dependency-check.py`. The permanent gate rejects
direct dependencies on Sales, Purchase, Inventory, MRP, HR, Accounting, Odoo
Quality, Maintenance, and related functional ERP modules. Standard technical
Odoo dependencies such as `base`, `mail`, and the existing `project` bridge for
implementation task UX are reported separately from Perfect Match dependencies.

## Demo Contract

The disposable `pmqms_demo` environment seeds one fictional Apex organization
and exactly three canonical sites:

- `APEX-HQ` — Headquarters & Quality Center (primary)
- `APEX-MFG` — Manufacturing Plant
- `APEX-INS` — Inspection & Distribution Center

The seed is deterministic and the validator checks names, codes, count,
company alignment, primary-site uniqueness, and per-code idempotency. The
Oliva pilot database is not touched.
