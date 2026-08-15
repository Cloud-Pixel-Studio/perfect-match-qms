# QMS Security Architecture

## Scope

This document defines the QMS security model for internal Odoo users through
Mission 07.
It does not implement customer portal access.

## Roles

`QMS User`

- Read QMS framework and implementation information within allowed companies.
- Submit evidence records where they have company access.
- Report operational risk, NCR, and CAPA records where justified.
- Cannot approve documents, accept/reject evidence, close NCRs, close risks, or
  close CAPAs.
- Can read audit records in allowed companies and submit audit evidence where
  evidence collection is requested.
- Cannot plan, start, complete, or cancel audits; issue findings; create NCRs
  from findings; or close findings.
- Can read performance data in allowed companies and enter KPI measurements or
  customer satisfaction measurements where operational entry is appropriate.
- Cannot configure objectives, KPI targets, supplier evaluations, or privileged
  performance configuration.
- Can read permitted management reviews and update management review actions
  assigned to them where the action workflow allows owner updates.

`QMS Manager`

- Create and update QMS framework and implementation records.
- Manage controlled documents and revisions.
- Review, accept, reject, and expire evidence.
- Assess, review, verify, and close risk, NCR, and CAPA records.
- Create and manage audit programs, audits, scope, criteria, plan lines, audit
  evidence, findings, auditor independence review, and finding-to-NCR handoff.
- Create and manage objectives, KPI definitions, KPI targets, customer
  performance, supplier performance, and supplier evaluations.
- Verify KPI measurements and complete supplier evaluations.
- Create and manage management reviews, generate snapshots, record decisions,
  create follow-up actions, complete reviews, and verify management review
  actions.
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

Mission 05 extends this to:

- audit programs;
- audits;
- audit scope;
- audit criteria;
- audit plan lines;
- audit evidence;
- audit findings.

Mission 06 extends this to:

- objectives;
- KPIs;
- KPI measurements;
- customer performance;
- customer satisfaction;
- supplier performance;
- supplier evaluations.

Mission 07 extends this to:

- management reviews;
- management review inputs;
- management review decisions;
- management review actions.

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

Mission 05 extends attachment linkage and tests to audit evidence attachments.
A user from another company cannot retrieve an audit evidence attachment through
a direct attachment read.

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
- audit program approve, activate, complete, cancel;
- audit plan, ready, start, reporting, complete, cancel;
- auditor independence confirmation or documented override;
- audit finding issue, accept, require action, create NCR, close, cancel.
- objective activate, achieved, not achieved, KPI evaluation, close, cancel;
- KPI activate, deactivate, reset;
- KPI measurement verification;
- supplier evaluation complete and cancel.

Direct state writes are blocked for controlled implementation, document,
revision, evidence, risk, NCR, CAPA, CAPA action, audit program, audit, and
audit finding states. Mission 06 also blocks direct status/state writes for
objectives, KPI definitions, and supplier evaluations. Mission 07 blocks direct
state/status writes for management reviews and management review actions.

Management review inputs are locked once a review is ready, in progress,
completed, or cancelled for normal users. Completed review history is corrected
only by QMS Administrators. Management review actions remain operational
follow-up records and may stay open after the meeting is completed.

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
- audit workflow authority, auditor independence requirements, finding
  workflow authority, finding-to-NCR rules, audit/NCR/CAPA lifecycle
  independence, multi-company audit isolation, relationship constraints, and
  protected audit attachment access.
- objective/KPI workflow authority, KPI snapshot integrity, user measurement
  entry, KPI verification authority, customer/supplier partner reuse,
  supplier evaluation authority, multi-company performance isolation,
  relationship constraints, and the rule that off-target KPI results do not
  automatically create NCR or CAPA records.
- management review workflow authority, historical snapshot integrity,
  snapshot locking, previous review action capture, owner action workflow,
  management review action verification authority, multi-company review/input/
  decision/action isolation, and snapshot generation that excludes other
  companies and organizations.
