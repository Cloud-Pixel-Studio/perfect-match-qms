# PMQMS-058 - Customer Quality, Complaints, 8D and SCAR

Priority: HIGH
Project: PMQMS CORE
Module: CAPA
Cycle: Backlog
Labels: odoo, backend, frontend, testing, documentation, compliance, pilot
Dependencies: PMQMS-057

## Objective

Build the post-rc3 Perfect Match customer and supplier quality layer for complaints, quality alerts, 8D cases, supplier issues, and SCAR while keeping NCR and CAPA as the authoritative QMS engines.

## Description

Implement `pm_qms_customer_quality` as a modular Odoo addon. Reuse `res.partner` for customers and suppliers, use neutral text references for external operational identifiers, integrate dashboard and management review signals, add demo-only fictional records, and verify the addon through automated tests and pilot-safe update procedures.

## Acceptance Criteria

- Customer complaints support containment, response tracking, NCR creation, 8D creation, quality alerts, and controlled closure.
- Supplier issues support containment, NCR creation, optional SCAR creation, and controlled closure without creating automatic CAPA records.
- SCAR supports supplier response history, returned revisions, accepted responses, effectiveness review, CAPA creation by explicit action, and closure.
- 8D supports D0-D8 sections, root-cause analysis, CAPA linkage, effectiveness review, and closure.
- Existing NCR and CAPA models remain authoritative and receive back-links rather than being replaced.
- The addon has no hard dependency on Odoo Sales, Purchase, Stock, MRP, or Quality.
- Dashboard and management review include customer/supplier quality signals.
- Security rules enforce QMS groups and company isolation.
- Automated tests cover core workflows, idempotent linking, alignment validation, dashboard/management review integration, and closure guards.
- DEV validation, GitHub Actions, and pilot-safe update validation pass before closure.
