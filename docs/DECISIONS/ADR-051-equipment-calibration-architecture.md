# ADR-051: Equipment, Monitoring Resources and Calibration Architecture

## Status

Accepted

## Context

Perfect Match QMS needs to control monitoring and measuring resources,
calibration status, calibration history, certificates, out-of-tolerance events,
retrospective impact assessment, and NCR/CAPA traceability.

Customers may use Odoo Maintenance, a different CMMS, a calibration provider's
portal, spreadsheets, or no asset-management system. A hard dependency on
Maintenance, MRP, Inventory, Odoo Quality, or a LIMS would make the QMS product
larger than the required scope and would force unrelated operational systems
onto customers.

An out-of-tolerance calibration is not only a scheduling problem. The product
must control the equipment, evaluate possible retrospective impact, document the
decision, and connect to NCR/CAPA only when the assessment justifies it.

## Decision

Mission 15 introduces `pm_qms_calibration` as a QMS-native addon.

The addon defines its own monitoring-resource master model,
`pm.qms.equipment`, with a stable equipment/gage identifier unique within the
QMS organization. Equipment type and calibration provider are configurable
records. Lifecycle status is stored separately from calculated calibration
schedule status.

Calibration and verification history is stored in
`pm.qms.calibration.event`. Accepted pass or conditional events update the
equipment schedule and may return equipment to service. Accepted historical
events are protected from normal edits.

Failed or out-of-tolerance events quarantine the equipment and create or reuse
`pm.qms.calibration.impact.assessment`. The assessment owns the retrospective
exposure window, impacted-record review, containment, disposition, and required
NCR/CAPA links.

Affected records use a future-compatible reference model rather than hard
dependencies on manufacturing, inventory, sales, or quality modules.

The addon integrates with existing QMS records:

- Evidence can reference calibration events.
- NCR and CAPA can trace back to equipment, events, and impact assessments.
- Dashboard counters show calibration attention items.
- New Management Review snapshots can include calibration resource status.
- People records can be used for responsible owners and internal technicians.

Readiness scoring is not changed by Mission 15.

## Consequences

Perfect Match QMS can answer which monitoring resources exist, whether they
require calibration or verification, whether they are current, which
certificates support them, which resources are overdue, which resources are
quarantined, what the exposure window was for an OOT event, and whether NCR or
CAPA was required.

The product remains deployable without Odoo Maintenance or metrology-lab
software. Future bridge modules may connect QMS equipment to Maintenance, MRP,
Inventory, Odoo Quality, or external calibration systems without changing the
core QMS model.

## Verification

Mission 15 verification includes Odoo tests for equipment identity, scheduling,
due-state calculations, idempotent reminders, calibration event workflows,
pass/OOT behavior, impact-assessment creation and closure, affected references,
NCR/CAPA traceability, evidence links, dashboard metrics, management-review
inputs, security boundaries, install/upgrade scripts, and full regression.
