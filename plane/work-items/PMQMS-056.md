# PMQMS-056 - Equipment, Monitoring Resources and Calibration Management

Priority: HIGH
Project: PMQMS PLATFORM
Module: Odoo Architecture
Cycle: Backlog
Labels: odoo, backend, testing, compliance, pilot, architecture
Dependencies: PMQMS-055

## Objective

Add a native Perfect Match QMS capability for monitoring and measuring resources,
calibration, verification, out-of-tolerance control, impact assessment, and
NCR/CAPA traceability.

## Description

Deliver Mission 15 as a reusable product module rather than a customer-specific
asset-management customization. The implementation must remain independent from
Odoo Maintenance, MRP, Inventory, Odoo Quality, and laboratory systems while
providing deterministic calibration scheduling, certificate support, historical
calibration events, OOT quarantine, exposure-window assessment, affected-record
references, and QMS integrations.

## Acceptance Criteria

- QMS equipment/monitoring-resource records have stable organization-scoped
  equipment IDs, lifecycle state, configurable type, owner, purpose, and
  calibration/verification requirements.
- Calibration scheduling calculates due, due-soon, overdue, current, no-history,
  and not-required status from accepted event history and interval configuration.
- Reminder generation is idempotent and uses native Odoo activities.
- Calibration and verification events preserve history, support certificates,
  internal/external workflow, pass, conditional, fail, and OOT results.
- Passed events can return equipment to service and update next due dates.
- Failed/OOT events quarantine equipment and create or reuse a linked impact
  assessment without silently returning equipment to service.
- Impact assessments capture last acceptable calibration, exposure window,
  affected references, containment, evaluation, disposition, approval, and
  required NCR/CAPA links.
- NCR and CAPA records trace back to equipment, calibration event, and impact
  assessment; CAPA is not automatically created for every failure.
- Evidence, People, Dashboard, Audit, and Management Review integrations are
  implemented without changing readiness scoring or historical snapshots.
- Demo records are fictional and optional; the Oliva pilot installs/upgrades
  without seeding calibration demo data.
- Automated tests, secret scan, content-safety scan, addon validation, pilot
  backup, pilot upgrade, HTTP health, documentation, ADR, GitHub CI, and final
  repository state all pass.
