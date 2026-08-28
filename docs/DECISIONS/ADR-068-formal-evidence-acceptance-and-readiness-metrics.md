# ADR-068: Formal Evidence Acceptance and Readiness Metrics

## Status

Accepted for Mission 25.8 implementation.

## Decision

Formal evidence definitions remain reusable, company-scoped QMS records. Each
seeded definition may have a stable definition key and Perfect Match-authored
acceptance criteria. The existing evidence requirement records are adopted by
stable key or by an exact legacy control/name match; ambiguous matches fail
loudly.

Evidence acceptance criteria describe observable review conditions for an
evidence set. They are generic QMS guidance and are not copied standard text.

Live readiness counts only active requirements, active evidence, and accepted evidence. Controls marked Not Applicable preserve their line-level evidence and activity traceability, but contribute neither required evidence nor required implementation activities to readiness-facing aggregates. Completed readiness assessments retain those line-level snapshots while excluding N/A lines from aggregate calculations.

The ISO 9001 add-on owns a reference-only crosswalk from its authored activity
keys to the generic evidence definitions. The generic QMS remains
standard-neutral. M25.8 does not import historical projects, chatter, users,
prompts, or customer data.

## Consequences

- Existing evidence records and relationships keep their database identities.
- Reviewers can see the requirement description and acceptance criteria from an
  evidence record.
- Archived or expired evidence cannot silently satisfy live readiness.
- Pack seeding is idempotent and rejects duplicate or incompatible definitions.
- No new Odoo model or direct historical data import is introduced.
