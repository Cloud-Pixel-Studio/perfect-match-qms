# ADR-011: QMS Security Model

Date: 2026-08-14

## Status

Accepted

## Context

Perfect Match Digital QMS needs a security model that supports framework
definitions, client implementation data, controlled documents, evidence, and
future portal access without exposing cross-client records.

## Decision

Use Odoo groups, ACLs, record rules, model constraints, and controlled workflow
actions.

Initial roles are:

- QMS User;
- QMS Manager;
- QMS Administrator.

Company isolation uses record rules on `company_id`. Organization isolation is
enforced by model constraints on relationships between organizations,
processes, control instances, documents, and evidence.

Direct state writes are blocked for controlled document, revision, and evidence
workflow fields. Users must use actions.

## Alternatives Considered

- Rely only on menu visibility. Rejected because it does not protect direct ORM
  or API access.
- Use direct SQL guards. Rejected because Odoo ORM, ACLs, and record rules are
  the platform security layer.
- Implement portal access now. Rejected because portal isolation needs a later
  focused design and test suite.

## Consequences

- Every new persisted QMS model needs ACLs and company rules before it is
  installable.
- Workflow actions must be tested with both permitted and denied users.
- Future portal work must extend this design instead of weakening it.
