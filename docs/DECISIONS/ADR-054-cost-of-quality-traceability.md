# ADR-054: Cost of Quality Data and Source Traceability Architecture

Status: Accepted
Date: 2026-08-22

## Context

Perfect Match QMS needs a way to quantify quality costs and COPQ after the RC4 operational modules. The capability must support prevention, appraisal, internal failure, external failure, recoveries, source traceability, analytics, and management review inputs. It must not become an accounting subsystem or depend on Sales, Purchase, Inventory, MRP, Odoo Quality, invoices, payroll, or general ledger entries.

## Decision

Implement `pm_qms_cost_quality` as an Odoo addon with cost types, cost events, and cost lines. Cost events are explicit user-entered records tied to an organization, optional process, optional allowlisted QMS source, company currency, and one or more lines.

COPQ is Internal Failure plus External Failure only. Prevention and Appraisal remain quality cost categories but are not COPQ. Recoveries are tracked as positive amounts and subtracted from gross quality cost to calculate net quality cost. Cost lines include an estimated marker so projected values are identifiable.

Confirmed cost events are protected from silent edits to core identity, date, source, and lines. Corrections are created as new draft correction events linked to the confirmed event. Official analytics and management review snapshots include confirmed events only.

## Consequences

- Quality cost reporting is available without accounting or ERP bridge dependencies.
- Historical confirmed cost events remain auditable.
- Source links are constrained to a safe allowlist and company/organization alignment is enforced.
- Multiple cost events can be recorded against the same source without fabricating costs automatically.
- Future ERP bridge addons may create optional links or imports, but the core Cost of Quality model remains independent.

## Verification

Mission 17 verification covers COPQ formulas, recoveries, estimated lines, workflow confirmation, immutability, correction events, source alignment, dashboard metrics, management review snapshots, Odoo install/update, and full Mission 17 regression.
