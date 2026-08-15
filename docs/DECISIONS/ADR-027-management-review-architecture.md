# ADR-027: Management Review Architecture

Date: 2026-08-15

## Status

Accepted

## Context

Perfect Match Digital QMS needs management review records after objectives,
KPIs, customer/supplier performance, audit, risk, NCR, and CAPA data are
available. Reviews must be client operational data and must not alter reusable
Perfect Match framework controls.

## Decision

Create `pm_qms_management_review` with:

- `pm.qms.management.review`;
- `pm.qms.management.review.input`;
- `pm.qms.management.review.decision`;
- `pm.qms.management.review.action`.

Reviews belong to one organization and company. They sit downstream of control
instances and operational QMS data.

## Consequences

Management Review can consolidate existing data without duplicating KPI,
customer, supplier, audit, risk, NCR, or CAPA systems. Future Mission 08 work
can consume completed review data as part of readiness and implementation
generation without moving review state onto framework controls.
