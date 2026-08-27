# ADR-066: ISO 9001 Initial Implementation Template and Pack-Scoped Activities

- Status: Accepted
- Date: 2026-08-27
- Scope: Mission 25.3 foundation

## Decision

ISO 9001 Initial Implementation is a separately versioned implementation pack
with code PM-QMS-ISO9001-INITIAL and version 1.0. It owns its 13
implementation phases and reviewed activity blueprint in pm_qms_iso9001.
The generic PM controls are reused; duplicate ISO-specific controls are not
created.

Implementation activities may optionally reference applicable framework packs.
An empty scope preserves legacy/global behavior. A populated scope limits future
task generation to implementation controls whose source packs overlap the
activity scope. Pack applicability answers whether an activity exists;
readiness_required remains the independent answer to whether that activity
participates in readiness.

Each control receives one primary phase in the ISO pack. Existing mapping
profiles remain separate from implementation methodology packs. The historical
M25.2 source is knowledge for review, not a production import, and its record
count is not preserved as a product rule.

## Content boundary

The blueprint is authored product metadata, not a source dump. It contains no
chatter, users, emails, AI prompts, customer identifiers, source database IDs,
transition content, other-standard content, or copied standard requirement text.
Deep objectives, guidance, evidence expectations, and success criteria are
reserved for later M25.4-M25.8 authoring work.

## Consequences

- pm_qms_implementation owns only generic pack-applicability mechanics.
- pm_qms_iso9001 depends downward on the generic implementation and quality
  pack layers.
- Existing empty-scope activities remain backward compatible.
- Future pack changes do not rewrite existing generated tasks.
- The ISO pack loader validates incompatible active definitions instead of
  silently rewriting them.
