# ADR-053: Unified Action Center Aggregation Architecture

Status: Accepted
Date: 2026-08-22

## Context

Perfect Match QMS now has actionable obligations across implementation, NCR, CAPA, audit, risk, management review, people, document acknowledgment, calibration, customer quality, supplier quality, and related workflows. Users need one place to answer what needs attention, but those source records already own their workflow state, due dates, assignments, and audit trails.

Creating a new authoritative action table would duplicate state and create synchronization, security, and auditability risks. A SQL union view was also rejected for Mission 17 because Odoo record rules, optional modules, and person-to-user ownership semantics are better preserved through ORM provider queries.

## Decision

Implement `pm_qms_action_center` as an Odoo addon that provides a current-user, ORM-backed provider registry and a transient presentation model, `pm.qms.action.center.line`.

The normalized action identity is `source_model`, `source_id`, and `action_kind`. Source records remain authoritative. Refreshing the Action Center rebuilds only the current user's transient projection from readable source records.

Provider collection uses the current user and does not use `sudo()` to collect source records. Source opening is server allowlisted by provider tuple and verifies model, record existence, and read access before returning the source form action.

## Consequences

- Action Center lines are non-authoritative and can be safely rebuilt.
- Existing source workflows, audit trails, and access rules remain authoritative.
- One source record can expose multiple distinct obligations without merging their semantics.
- The design avoids a generic model opener and prevents arbitrary source navigation.
- Future performance work may add an explicit rebuildable cache, but it must remain non-authoritative and source-linked.

## Verification

Mission 17 verification covers provider collection, idempotent refresh, allowlisted source opening, unsafe opener rejection, dashboard counts, Odoo install/update, and full Mission 17 regression.
