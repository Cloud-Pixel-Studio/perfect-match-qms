# ADR-038: Quality Management Pack Architecture

Date: 2026-08-15

## Status

Accepted

## Context

Mission 08 delivered a generic implementation engine, but Perfect Match still
needed its first commercial quality-management pack. The pack must be useful
for client project generation while preserving the repository's IP boundary.

## Decision

Create `pm_qms_pack_quality` as a separate addon that depends on
`pm_qms_core` and `pm_qms_implementation`.

The addon seeds a versioned framework pack named `Perfect Match Quality
Management Pack`, code `PM-QMS-QUALITY`, version `1.0`. Pack controls are
Perfect Match-authored reusable controls with implementation activities and
mandatory evidence expectations. The pack is activated during module
installation through Odoo ORM logic.

## Consequences

The commercial quality pack can be installed, tested, versioned, and deployed
without changing the generic implementation engine into a quality-specific
module. Future packs can follow the same pattern.
