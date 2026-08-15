# ADR-023: Objective And KPI Architecture

Date: 2026-08-15

## Status

Accepted

## Context

Perfect Match Digital QMS needs performance data for future Management Review,
readiness, dashboards, AI summaries, and automation. Objectives and KPIs are
client operational data, not reusable framework definitions.

## Decision

Create `pm_qms_kpi` with separate models for:

- `pm.qms.objective`
- `pm.qms.kpi`
- `pm.qms.kpi.measurement`

Objectives and KPIs relate to `pm.qms.control.instance` and `pm.qms.process`.
They do not store mutable client objectives or KPI results on `pm.qms.control`.

`pm.qms.kpi` defines what is measured. `pm.qms.kpi.measurement` stores actual
performance by period.

## Consequences

The design supports one objective to many KPIs and one KPI to many objectives.
Historical results remain queryable for future Management Review without
polluting reusable Perfect Match framework controls.
