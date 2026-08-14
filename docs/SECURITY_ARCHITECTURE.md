# QMS Security Architecture

## Scope

This document defines the QMS security model for internal Odoo users through
Mission 04.
It does not implement customer portal access.

## Roles

`QMS User`

- Read QMS framework and implementation information within allowed companies.
- Submit evidence records where they have company access.
- Report operational risk, NCR, and CAPA records where justified.
- Cannot approve documents, accept/reject evidence, close NCRs, close risks, or
  close CAPAs.

`QMS Manager`

- Create and update QMS framework and implementation records.
- Manage controlled documents and revisions.
- Review, accept, reject, and expire evidence.
- Assess, review, verify, and close risk, NCR, and CAPA records.
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

Mission 04 extends this to:

- operational events;
- risks and opportunities;
- nonconformities;
- CAPAs;
- CAPA actions;
- CAPA 5 Why entries.

Organization isolation is enforced by model constraints where relationships
must belong to the selected organization. Documents, evidence, and control
instances reject mismatched process, organization, or company relationships.

## Attachments

QMS records reference files through Odoo `ir.attachment`. Custom QMS models do
not duplicate binary storage. Mission 04 links evidence, risk, NCR, and CAPA
attachments back to their owning QMS records so Odoo attachment checks can
evaluate access through the protected record.

Tests verify that a user from another company cannot retrieve a protected risk
attachment through a direct attachment read.

## Administrative Boundaries

Workflow state changes use model actions:

- document submit, approve, reject, activate, obsolete;
- revision submit, approve, reject, activate, supersede;
- evidence submit, review, accept, reject, expire.
- risk assess, require action, monitor, review, close;
- NCR open, containment, investigation, action required, verification, close;
- CAPA analysis, action planning, implementation, effectiveness review,
  effective/ineffective decision, reopen, close;
- CAPA action start, complete, verify, cancel.

Direct state writes are blocked for controlled implementation, document,
revision, evidence, risk, NCR, CAPA, and CAPA action states.

`pm.qms.event` is append-only at the ORM level for normal QMS groups. Workflow
methods append events with the acting user, timestamp, previous state, new
state, decision, reviewer/approver where relevant, and notes where useful.
Odoo administrators with technical access remain technically capable of
database-level changes; this is documented rather than falsely presented as
cryptographic immutability.

## Future Portal Principles

Portal users are not implemented yet. Future portal access must:

- use a separate portal group and explicit record rules;
- expose only assigned client implementation records;
- avoid framework configuration write access;
- avoid direct attachment URLs without record ownership checks;
- include tests for every exposed model.

## Validation

Mission 03 and Mission 04 tests validate:

- QMS User read/submission limits;
- QMS Manager workflow authority;
- multi-company isolation for control instances, documents, revisions,
  evidence, risk, NCR, and CAPA;
- relationship constraints for organization and company boundaries;
- unauthorized closure prevention;
- protected attachment access;
- workflow event history for critical transitions.
