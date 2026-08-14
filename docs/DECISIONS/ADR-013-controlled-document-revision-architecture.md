# ADR-013: Controlled Document Revision Architecture

Date: 2026-08-14

## Status

Accepted

## Context

Controlled documents need stable identity and auditable revision history. The
current revision changes over time, but the document identity, links to
processes, controls, and evidence should remain stable.

## Decision

Use two models:

- `pm.qms.document` for document identity;
- `pm.qms.document.revision` for revision history and approval lifecycle.

Files are linked with `ir.attachment`.

Only one revision should be active at a time. Activating a new revision
supersedes the prior active revision. Historical revisions are not deleted.

## Alternatives Considered

- Store revision fields directly on the document only. Rejected because it loses
  history and makes approvals difficult to audit.
- Store every revision as a separate document. Rejected because it fragments the
  stable document identity and evidence relationships.

## Consequences

Document forms can show current revision while preserving full history.
Evidence may refer to the controlled document identity without duplicating file
storage.
