# ADR-028: Management Review Historical Snapshot Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Management Review must preserve what management reviewed. If completed reviews
query live KPI targets, findings, CAPA states, or objective status, historical
review evidence can change after the meeting.

## Decision

Store review inputs in `pm.qms.management.review.input`.

Generated inputs preserve category, title, description, snapshot date, status
snapshot, numeric value, text value, unit, target snapshot, reviewed period,
source type, and a safe source identifier.

Draft and preparing reviews may regenerate system-generated inputs. Manual
inputs are preserved. Ready and completed reviews are locked against normal
snapshot regeneration or mutation.

## Consequences

Completed reviews are historical records rather than live dashboards. Normal
correction of completed review input history is not allowed; administrator
correction remains a controlled exception.
