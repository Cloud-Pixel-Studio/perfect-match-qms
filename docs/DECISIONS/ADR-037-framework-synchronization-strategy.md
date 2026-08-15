# ADR-037: Framework Synchronization Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Implementation projects may need to synchronize after pack selection changes or
after new reusable activities are added. Synchronization must not erase client
execution history.

## Decision

Framework synchronization is additive and preservation-oriented. It validates
active packs, creates a native Odoo project if requested, resolves and
deduplicates pack controls, creates missing implementation controls, links all
source packs, reuses or creates control instances, and creates missing
generated tasks.

The first synchronization moves a draft implementation project to generated.
Later synchronization updates missing generated scope but does not delete
controls, tasks, evidence, or assessments.

## Consequences

The engine supports repeatable generation and resynchronization while
preserving operational traceability. Removing or retiring scope requires an
explicit future migration or closure policy rather than silent deletion.
