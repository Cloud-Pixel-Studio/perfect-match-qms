# ADR-033: Shared Control Deduplication And Control Instance Reuse

Date: 2026-08-15

## Status

Accepted

## Context

A control can appear in more than one framework pack. A client organization may
already have an operational control instance for a reusable control before a
new implementation project is generated.

## Decision

During framework synchronization, resolve all active pack-control lines into a
single control set. If the same control appears in multiple packs, create one
implementation control line and retain all source pack references. Required
status is merged with an OR rule.

For each organization and reusable control, reuse the existing active
`pm.qms.control.instance` when available. If none exists, create one. A unique
constraint prevents duplicate organization/control instances.

## Consequences

Shared controls are implemented once per organization. Evidence, documents,
risks, NCRs, CAPAs, audits, performance records, management reviews, generated
tasks, and readiness all point to the same operational implementation record.
