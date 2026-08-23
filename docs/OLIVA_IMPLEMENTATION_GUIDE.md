# Oliva Torras Implementation Guide

> **Historical, retired in RC6.** This guide records the former pilot and is
> not an active deployment or customer onboarding instruction.

This guide describes the next controlled steps for turning the technical pilot
into a real Oliva Torras implementation.

## Scope

Mission 10 created the technical foundation:

- An isolated Odoo pilot stack.
- Company and QMS organization records for `Oliva Torras USA, Inc.`
- The `PM-QMS-QUALITY` version `1.0` pack deployed into a generated project.
- 37 implementation controls, 74 generated tasks, and 37 evidence requirements.
- A controlled CSV migration addon for document and evidence metadata.
- Backup and restore scripts for the pilot stack.

The guide does not assume or invent customer users, process owners, suppliers,
customers, documents, KPIs, risks, NCRs, CAPAs, audits, or management review
content.

## Required Customer Inputs

Before production onboarding, collect authorized inputs from Oliva:

- Named project sponsor and implementation owner.
- Approved user list with roles and email addresses.
- Process inventory and process owners.
- Current controlled document inventory.
- Current evidence and record inventory.
- Customer and supplier master data approved for QMS use.
- KPI definitions, targets, periods, and data owners.
- Open risks, NCRs, CAPAs, audit findings, and management actions that Oliva
  authorizes for migration.
- External standard mapping CSV reviewed and approved by authorized human
  reviewers, if external mapping coverage is needed.

## Implementation Sequence

1. Confirm pilot access and roles with Oliva-approved users.
2. Load or verify organization processes in Odoo.
3. Review the 37 generated Quality Pack controls with the customer.
4. Assign owners and due dates to generated implementation tasks.
5. Import controlled document metadata through the document import wizard.
6. Import evidence metadata through the evidence import wizard.
7. Review and accept evidence through QMS workflow only after customer approval.
8. Mark control instances implemented only when evidence and activities support
   the decision.
9. Run readiness assessments after each major implementation batch.
10. Record risks, NCRs, CAPAs, audits, KPIs, and management reviews as actual
    customer operational data only after authorization.

## Migration Controls

Use `pm_qms_migration` for CSV-based imports.

Document import creates only the current revision from an authorized inventory.
It does not fabricate historical revisions or approvals.

Evidence import can create records in `draft`, `submitted`, `under_review`, or
`rejected`. It intentionally rejects `accepted`; acceptance must pass through
the QMS evidence review workflow.

All imported records should include a migration note identifying source,
authorization, and scope.

## Readiness Interpretation

Readiness is an internal implementation metric:

```text
ready applicable controls / total applicable controls * 100
```

It is not:

- Certification.
- External standard compliance.
- Audit outcome prediction.
- A substitute for customer approval.

Mission 10 validation reached 2.7027 percent because one pilot validation
control was exercised end to end. That is a technical proof, not customer
implementation completion.

## Known Gaps Before Go-Live

- No authorized Oliva users beyond technical validation users.
- No real Oliva document inventory imported.
- No real Oliva evidence accepted.
- No real Oliva KPI or performance data loaded.
- No customer-approved external mapping CSV loaded.
- No customer portal workflow implemented.
- No AI assistant workflow implemented.
- No n8n production automation implemented.
- No public pilot DNS/TLS route configured.
- Multi-standard packs remain future work.
