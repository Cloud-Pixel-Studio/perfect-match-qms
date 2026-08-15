# ADR-042: Shared Generic Vs Quality Specific Control Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Some controls may be useful across many future packs, while others are specific
to quality-management implementation. The system needs reuse without losing the
meaning of the commercial quality pack.

## Decision

Keep the implementation engine generic and let packs choose their reusable
controls. Mission 09 seeds quality-specific commercial controls in
`pm_qms_pack_quality`, while Mission 08 keeps multi-pack deduplication in the
generic engine.

If a later pack shares a control, the generator creates one implementation
control line and preserves all source pack references. If a quality pack
control belongs to a framework organization process, the generator creates or
reuses an equivalent process for the client organization before creating the
control instance.

## Consequences

Future standard packs can reuse common controls without duplicating client
implementation records. Quality-specific controls can still carry the domain
language and evidence expectations needed for a commercial QMS deployment.
