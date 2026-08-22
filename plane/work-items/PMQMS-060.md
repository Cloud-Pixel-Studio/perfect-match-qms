# PMQMS-060 - Implement Cost of Quality and Unified Action Center

Priority: HIGH
Project: PMQMS PLATFORM
Module: Reporting
Cycle: Backlog
Labels: odoo, feature, reporting, testing, architecture, pilot
Dependencies: PMQMS-059

## Objective

Implement Mission 17 product capabilities for a non-authoritative unified action center and a traceable Cost of Quality layer.

## Description

Create Odoo addons for action aggregation and quality cost capture without replacing source workflows, accounting systems, or the KPI engine. Include dashboard metrics, source navigation, controlled cost categories, COPQ formulas, management review inputs, tests, documentation, and Oliva Torras pilot validation.

## Acceptance Criteria

- Unified Action Center aggregates readable QMS obligations without becoming the authoritative workflow state.
- Source records remain authoritative and source opening is server allowlisted.
- Cost of Quality supports prevention, appraisal, internal failure, external failure, recoveries, estimated lines, and confirmed-only analytics.
- COPQ equals internal failure plus external failure only.
- Confirmed cost events are protected and corrections are created as draft linked records.
- Dashboard and management review include Mission 17 metrics and snapshots.
- Oliva Torras pilot installs Mission 17 without demo Cost Events and validates HTTP health.
- Documentation and ADRs describe architecture, formulas, traceability, security, and pilot policy.
- Mission 17 Odoo regression and auxiliary quality gates pass.
