# ADR-029: Management Review Inputs And Source Aggregation

Date: 2026-08-15

## Status

Accepted

## Context

Management Review needs input from many operational models. A generic SQL,
Python expression, or arbitrary model reference engine would create security
and maintainability risk.

## Decision

Implement source aggregation as controlled Odoo ORM logic in the Management
Review addon. Each source uses explicit domains for company, organization, and
period.

The first sources are objectives, KPI measurements, customer performance,
customer satisfaction, supplier performance, supplier evaluations, audits,
audit findings, risks, opportunities, NCR, CAPA, and previous review actions.

## Consequences

The snapshot engine is safe and testable. Future sources can be added as
explicit provider methods or a documented provider service without exposing
arbitrary query execution to users.
