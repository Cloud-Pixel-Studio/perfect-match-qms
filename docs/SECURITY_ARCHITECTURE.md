# QMS Security Architecture

## Scope

This document defines the Mission 03 QMS security model for internal Odoo users.
It does not implement customer portal access.

## Roles

`QMS User`

- Read QMS framework and implementation information within allowed companies.
- Submit evidence records where they have company access.
- Cannot approve documents or accept/reject evidence.

`QMS Manager`

- Create and update QMS framework and implementation records.
- Manage controlled documents and revisions.
- Review, accept, reject, and expire evidence.
- Cannot bypass company record rules.

`QMS Administrator`

- Full QMS configuration permissions.
- Can delete draft/configuration records where model constraints allow it.
- Still operates through Odoo access controls and record rules.

## Isolation

Company isolation is enforced with Odoo record rules using:

```text
company_id in company_ids
```

Mission 03 applies this to:

- organizations;
- processes;
- framework controls;
- control instances;
- controlled documents;
- document revisions;
- evidence records.

Organization isolation is enforced by model constraints where relationships
must belong to the selected organization. Documents, evidence, and control
instances reject mismatched process, organization, or company relationships.

## Attachments

QMS records reference files through Odoo `ir.attachment`. Custom QMS models do
not duplicate binary storage. Attachment security follows Odoo attachment rules
plus the access path through the owning document or evidence record.

## Administrative Boundaries

Workflow state changes use model actions:

- document submit, approve, reject, activate, obsolete;
- revision submit, approve, reject, activate, supersede;
- evidence submit, review, accept, reject, expire.

Direct state writes are blocked for document, revision, and evidence states.

## Future Portal Principles

Portal users are not implemented yet. Future portal access must:

- use a separate portal group and explicit record rules;
- expose only assigned client implementation records;
- avoid framework configuration write access;
- avoid direct attachment URLs without record ownership checks;
- include tests for every exposed model.

## Validation

Mission 03 tests validate:

- QMS User read/submission limits;
- QMS Manager workflow authority;
- multi-company isolation for control instances, documents, revisions, and evidence;
- relationship constraints for organization and company boundaries.
