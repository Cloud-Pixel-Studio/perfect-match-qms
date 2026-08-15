# ADR-024: KPI Historical Target Snapshot

Date: 2026-08-15

## Status

Accepted

## Context

KPI targets change over time. If historical measurements read the current KPI
target dynamically, prior results could appear to change after target updates.

## Decision

`pm.qms.kpi.measurement` stores target, warning, and direction snapshots at the
time the measurement is recorded.

Status calculation uses those snapshots. Changing `pm.qms.kpi` target
configuration logs an event but does not rewrite existing measurements.

## Consequences

Historical KPI evidence remains stable. Correcting a historical snapshot is an
administrator-level data correction rather than normal KPI configuration.
