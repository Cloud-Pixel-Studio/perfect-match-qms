# ADR-034: Project Task Generation Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Implementation work should be executable by users in normal Odoo project tools,
but reusable activity definitions must remain unchanged framework content.

## Decision

Generate native `project.task` records from active `pm.qms.activity` records.
Generated tasks keep references to:

- the implementation project;
- the implementation control;
- the control instance;
- the reusable activity.

Task completion is evaluated with Odoo's native task closure mechanism through
`project.task.is_closed`. The engine does not infer completion from stage names
because stage names are configurable and translatable.

## Consequences

Users can manage execution in Odoo Projects while the QMS engine retains a
traceable link back to generated scope. Reusable activities stay reusable and
are not mutated by project execution.
