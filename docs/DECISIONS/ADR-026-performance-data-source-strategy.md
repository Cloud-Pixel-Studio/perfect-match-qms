# ADR-026: Performance Data Source Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Performance measurements may be entered manually, calculated from Odoo records,
or imported from integrations. Allowing arbitrary SQL or Python formulas would
create security and maintainability risk.

## Decision

Use explicit source categories:

- manual
- system calculated
- integration

Mission 06 does not implement a generic SQL engine, Python formula engine, or
user-executable expression language. Future calculated metrics must be
implemented as controlled application logic or approved integrations.

## Consequences

The performance layer is safe for operational use now and remains extensible for
future Odoo Purchase, Inventory, external integration, and automation work.
