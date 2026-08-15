# ADR-036: Historical Readiness Assessment Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Live implementation status, evidence, and task completion change over time.
Perfect Match needs completed readiness assessments to preserve what was known
at the assessment date.

## Decision

Create `pm.qms.readiness.assessment` and
`pm.qms.readiness.assessment.item`. Completing an assessment copies control
code, control name, applicability, implementation status, evidence counts,
activity counts, readiness state, gap reason, and source pack references into
assessment items.

Completed assessments and completed assessment items are locked against normal
mutation or deletion.

## Consequences

Historical readiness reports remain stable after live implementation improves
or changes. Future reports can compare assessment history without relying on
current operational state.
