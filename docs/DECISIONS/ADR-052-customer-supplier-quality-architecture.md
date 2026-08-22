# ADR-052: Customer and Supplier Quality Architecture

Status: Accepted
Date: 2026-08-21

## Context

Perfect Match QMS needs a post-rc3 customer and supplier quality layer for customer complaints, quality alerts, 8D cases, supplier issues, and supplier corrective action requests. The existing Odoo QMS baseline already contains authoritative NCR and CAPA engines, document control, evidence, KPI, management review, people, calibration, dashboards, and audit support.

The new capability must not create a parallel NCR or CAPA subsystem. It must also stay deployable for service and consulting customers that may not use Odoo Sales, Purchase, Inventory, Manufacturing, or the standard Odoo Quality app.

## Decision

Create a single Odoo addon, `pm_qms_customer_quality`, for customer and supplier quality orchestration.

The addon introduces these records:

- `pm.qms.customer.complaint`
- `pm.qms.quality.alert`
- `pm.qms.root.cause.analysis` and `pm.qms.root.cause.line`
- `pm.qms.eight.d`
- `pm.qms.supplier.issue`
- `pm.qms.scar` and `pm.qms.scar.response`

The addon extends the existing NCR and CAPA models with links back to complaints, supplier issues, SCARs, and 8D cases. NCR remains the system of record for nonconformity control. CAPA remains the system of record for corrective and preventive actions. Complaint, 8D, supplier issue, and SCAR records may create or link NCR/CAPA records through explicit workflow actions only.

Customer and supplier identity uses Odoo `res.partner`. Product, order, lot, purchase order, and shipment references are stored as neutral text references so the addon has no hard dependency on sales, purchase, stock, manufacturing, or quality modules.

## Consequences

- The implementation stays compatible with the modular Odoo monolith architecture.
- Customer and supplier quality workflows can be installed in the Oliva pilot without seeding fictional customer or supplier records.
- NCR and CAPA reporting remains consolidated because no competing engines are introduced.
- Future optional integrations may add fields or smart buttons for sales, purchase, stock, MRP, or Odoo Quality records through separate bridge addons.
- External standards are not copied or reconstructed; the addon uses proprietary Perfect Match wording and stores only generic operational references.

## Verification

Mission 16 verification requires Python compilation, addon manifest/XML validation, secret scan, external-standard content safety scan, shell syntax validation, git diff checks, Odoo install/update, full Mission 16 Odoo tests, GitHub Actions, and pilot smoke validation.
