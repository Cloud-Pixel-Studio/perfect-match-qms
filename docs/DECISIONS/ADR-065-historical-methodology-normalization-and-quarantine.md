# ADR-065: Historical Methodology Normalization and Quarantine

## Status

Accepted for Mission 25.2 implementation.

## Context

The historical Perfect Match methodology package is useful source knowledge
for future ISO 9001 Initial Implementation authoring. It is an export from a
source environment, not a product data migration. It contains project/task
records, chatter, users, tags, technical metadata, and source-derived prose
that cannot be treated as approved customer content.

## Decision

Use a deterministic local normalization tool under `tools/methodology/`.
The original package remains external to Git, and generated source-derived
JSON reports remain in an ignored workspace outside tracked production
content. The tool creates safe structural provenance keys from hashed
content/position rather than using historical database IDs as product IDs.

The tool:

- inventories the archive and validates its expected SHA-256;
- excludes chatter, authors, users, email addresses, attachments, source IDs,
  environment metadata, and raw AI prompts;
- classifies main tasks and subtasks using explicit, reviewable taxonomy;
- gives explicit source stage and task title precedence over shared metadata;
- treats a generic year such as \`2026\` as insufficient transition evidence;
- preserves semantic subtask categories and safe parent context, including for
  transition parents;
- separates project administration, transition work, readiness assessment,
  certification preparation, and gap remediation from Initial Implementation;
- quarantines other-standard references and possible protected standard text;
- preserves unresolved tags, duplicate candidates, and low-confidence items for
  review instead of forcing false certainty;
- emits deterministic JSON and manifest hashes; and
- never imports historical `project.task` records or changes Odoo runtime
  models.

The output is `SOURCE_DERIVED_CANDIDATE` knowledge only. It is not final
Perfect Match-authored content and cannot be exposed to customers without a
later review and authoring checkpoint. ISO 9001 references may be retained as
external metadata; copied requirement text is not approved. Other standards
and transition content remain separate from the ISO 9001 Initial
Implementation dataset.

## Consequences

M25.3 can use reviewed local candidates to author a native framework pack
while keeping customer transactional state separate. Repeated source content
is visible as a review signal instead of becoming duplicate controls or
activities. The historical package remains auditable as external source
material without leaking source users, customer identifiers, or technical
metadata into Git.

The normalizer reports trigger-field diagnostics and distribution warnings so
classification contamination is visible during source review. It intentionally
does not decide final wording, compliance claims,
or readiness behavior. Those decisions belong to later authoring and review
work.
