# Perfect Match QMS Internal Audit

`pm_qms_audit` implements the reusable internal audit foundation for Perfect
Match Digital QMS.

## Architecture

```text
Audit Program
      |
      v
Audit
 |-- Scope
 |-- Criteria
 |-- Team
 |-- Plan
 |-- Evidence
 `-- Findings
        |
        v
       NCR
        |
        v
       CAPA
```

## Models

- `pm.qms.audit.program`: planned internal audit programs.
- `pm.qms.audit`: individual audits with planning, team, independence review,
  lifecycle, summary counts, and conclusion.
- `pm.qms.audit.scope`: normalized organization, process, and control instance
  scope.
- `pm.qms.audit.criterion`: criteria using Perfect Match controls, company
  procedures, customer/regulatory references, external reference metadata, or
  other internal references.
- `pm.qms.audit.plan.line`: lightweight audit agenda and interview planning.
- `pm.qms.audit.evidence`: evidence collected during an audit.
- `pm.qms.audit.finding`: conformities, observations, opportunities for
  improvement, and internal nonconformities.

## Workflow

Audits move through:

```text
draft -> planned -> ready -> in_progress -> reporting -> completed
```

Findings move through:

```text
draft -> issued -> accepted/action_required -> closed
```

Only findings classified as internal nonconformity can create NCRs through the
normal workflow. Audit completion does not close findings, NCRs, or CAPAs.

## Security

QMS Users can read permitted audit records and create audit evidence. QMS
Managers manage audit lifecycle, issue findings, and create NCRs from findings.
QMS Administrators have full module administration.

All records are company-bound through record rules. Relationship constraints
protect organization and company alignment.

## IP Boundary

No external standard text belongs in this addon. External standards may be
referenced by metadata only, such as standard name and reference identifier.
