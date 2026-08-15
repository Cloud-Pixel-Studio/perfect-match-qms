# Mission 06 Plan: Performance KPI Customer Supplier Foundation

## Objective

Build the Perfect Match performance-management foundation for objectives, KPI
definitions, KPI measurements, customer performance, customer satisfaction,
supplier performance, and supplier evaluations.

## Business Requirement

Future Management Review, readiness, dashboards, AI summaries, and automation
need normalized performance data without implementing those future features yet.

## Technical Approach

Create `pm_qms_kpi` as a client operational addon. Keep the addon name even
though it includes objectives and partner performance. Separate KPI definitions
from historical KPI measurements. Reuse `res.partner` for customer and supplier
masters. Use existing NCR source categories for customer and supplier metrics
where structured data exists.

## Components Affected

- New addon: `addons/pm_qms_kpi`.
- DEV script and CI workflow.
- Architecture, security, testing, operational hardening, README, changelog,
  and ADR documentation.

## Database Changes

New models:

- `pm.qms.objective`
- `pm.qms.kpi`
- `pm.qms.kpi.measurement`
- `pm.qms.customer.performance`
- `pm.qms.customer.satisfaction`
- `pm.qms.supplier.performance`
- `pm.qms.supplier.evaluation`

Extensions:

- `pm.qms.control.instance`
- `pm.qms.process`
- `res.partner` relationship fields

## Security Implications

All persisted models receive ACLs and company-boundary record rules. QMS Users
can read performance data and enter operational KPI/satisfaction measurements.
QMS Managers configure objectives, KPI targets, customer/supplier performance,
and supplier evaluations. QMS Administrators retain full addon access.

## Dependencies

`pm_qms_kpi` depends on `pm_qms_ncr` so it can reuse existing risk/NCR
relationships and source-type metrics without duplicating complaint or supplier
quality events.

## Testing Strategy

Add post-install Odoo tests for objectives, KPI calculations, snapshots,
schedules, customer performance, customer satisfaction, supplier performance,
supplier evaluations, multi-company isolation, relationship constraints, and the
cross-module off-target KPI to risk scenario without automatic NCR/CAPA
creation.

## Acceptance Criteria

- Previous mission tests still pass.
- `pm_qms_kpi` installs and updates.
- KPI measurement snapshots remain preserved after target changes.
- Customer and supplier performance reuse `res.partner`.
- Multi-company isolation works for all new models.
- CI, secret scan, backup validation, Odoo health, Plane health, and Plane API
  updates pass.

## Rollback Considerations

The addon is modular. Roll back by reverting the Mission 06 commit or disabling
`pm_qms_kpi` in DEV. The migration does not alter reusable `pm.qms.control`
data or Plane data directly.
