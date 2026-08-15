# ADR-044: Controlled Migration Import Strategy

## Status

Accepted

## Context

Customer onboarding will need document and evidence migration, but Mission 10
must not invent Oliva documents, approvals, or evidence.

## Decision

Add `pm_qms_migration` with manager-only CSV import wizards:

- Document import creates a document and one current revision from an authorized
  inventory.
- Evidence import creates evidence in `draft`, `submitted`, `under_review`, or
  `rejected`.
- Evidence import rejects `accepted` state so acceptance always requires QMS
  workflow review.
- Attachments are accepted only as base64 file payloads with file names, not
  paths.
- Organization, process, owner, control instance, document, and evidence
  requirement references are validated before records are created.

## Consequences

Migration is repeatable and auditable, while avoiding fabricated revision
history or bypassed evidence approval. Larger customer migrations can extend
this strategy without weakening workflow controls.
