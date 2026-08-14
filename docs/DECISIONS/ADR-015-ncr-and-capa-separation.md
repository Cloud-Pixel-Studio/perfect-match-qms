# ADR-015: NCR and CAPA Separation

Date: 2026-08-14

## Status

Accepted

## Context

A nonconformity records a detected deviation. CAPA records correction or
prevention work and later effectiveness review. Combining them would make every
NCR look like a corrective action and would weaken traceability for cases where
an NCR does not require CAPA.

## Decision

Use `pm.qms.nonconformity` for NCR and `pm.qms.capa` for CAPA.

NCR can create CAPA through a controlled action. The CAPA stores a structured
`source_ncr_id` relationship and copies only minimal context needed to begin
the corrective action.

## Consequences

NCR records can close with appropriate disposition and verification while CAPA
keeps its own root cause, action, implementation, and effectiveness lifecycle.
Future audit findings can become another structured CAPA source without
rewriting NCR.
