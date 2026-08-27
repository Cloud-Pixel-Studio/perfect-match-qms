# ADR-067: Guided Activity Definitions and Narrative Evidence Expectations

- Status: Accepted
- Date: 2026-08-27
- Scope: Mission 25.4 guided implementation content

## Decision

The first ten ISO 9001 Initial Implementation activities are authored as a
reviewed content block in `pm_qms_iso9001` and materialized into the existing
`pm.qms.activity` model. They use stable `definition_key` values such as
`ISO9001-INITIAL-A001`; the key is indexed, unique within a company when
populated, and immutable once assigned. Legacy activities may remain without a
key.

Activity-specific methodology guidance is exposed on generated `project.task`
records through read-only related fields. The activity definition remains the
authoritative source while task status, assignment, deadline, and completion
remain execution data.

`evidence_expectations` is narrative guidance about objective evidence. It does
not create or replace `pm.qms.evidence.requirement` records and does not alter
readiness calculations. ISO-specific structured evidence requirements remain
deferred to M25.8.

Content is authored in checkpoint blocks. M25.4 materializes only A001-A010;
A011-A037 remain blueprint-only. The loader validates the authored block
against the structural blueprint, preserves the active pack mappings, and
fails explicitly when an existing seeded definition is incompatible.

## Boundaries

- The generic QMS remains standard-neutral.
- No new model, readiness engine, or automatic backfill of existing projects is
  introduced.
- No historical project tasks, chatter, users, prompts, customer identifiers,
  or source-derived datasets are imported.
- No official standard requirement text is copied or reconstructed.

## Consequences

New ISO Initial Implementation projects can receive ten authored guided
activities through the existing pack-scoped generation path. Re-running the
supported seed is deterministic and does not create duplicate definitions.
Later content blocks can be added independently after review without rewriting
historical customer execution records.
