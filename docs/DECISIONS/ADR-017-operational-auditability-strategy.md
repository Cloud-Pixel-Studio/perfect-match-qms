# ADR-017: Operational Auditability Strategy

Date: 2026-08-14

## Status

Accepted

## Context

Mission 03 models already use Odoo chatter tracking. Mission 04 introduces
more compliance-sensitive transitions around review, closure, and
effectiveness decisions.

## Decision

Keep `mail.thread` and field tracking for normal history. Add a lightweight
`pm.qms.event` append-only model for critical workflow transitions.

The event log records user, timestamp, model, record id, previous state, new
state, decision, reviewer, approver, and notes where useful. Workflow methods
append events centrally through a shared mixin.

## Consequences

The design avoids event-sourcing complexity while making critical decisions
queryable. It does not claim cryptographic immutability; Odoo administrators
and database administrators remain powerful and must be governed operationally.
