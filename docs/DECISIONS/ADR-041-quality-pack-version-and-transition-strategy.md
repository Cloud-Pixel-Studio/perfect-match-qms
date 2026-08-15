# ADR-041: Quality Pack Version And Transition Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Quality methodology and external publications change over time. Existing
client implementations and readiness assessments must continue to explain what
pack version and mapping profile were used at the time.

## Decision

Treat `PM-QMS-QUALITY` version `1.0` as the first active commercial quality
pack. Active and retired pack definitions stay locked through the Mission 08
pack rules.

External mapping profiles are versioned by profile code, edition, and company.
A new external publication or major mapping revision should be represented by a
new mapping profile, and a substantive methodology change should be
represented by a new pack version.

## Consequences

Historical implementation projects and readiness snapshots remain traceable.
Future transitions can compare old and new profiles or pack versions instead
of rewriting past records.
