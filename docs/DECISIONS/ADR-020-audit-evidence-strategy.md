# ADR-020: Audit Evidence Strategy

Date: 2026-08-14

## Status

Accepted

## Context

Mission 03 introduced `pm.qms.evidence` for implementation evidence tied to a
control instance and evidence requirement. Internal audits also collect
evidence, but audit evidence can come from interviews, observations, samples,
document review, or system reports and may be tied to an audit criterion rather
than a predefined implementation evidence requirement.

## Decision

Create `pm.qms.audit.evidence` for evidence collected during an audit.

Audit evidence can still reference:

- audit;
- criterion;
- document;
- control instance;
- collector;
- collection date;
- attachment.

It does not replace `pm.qms.evidence`. When an audit finding creates an NCR, the
NCR preserves source audit evidence through a structured relationship.

## Alternatives Considered

- Force audit evidence into `pm.qms.evidence`. Rejected because that model
  requires implementation evidence concepts that are not always valid during an
  audit.
- Store audit evidence only as text on findings. Rejected because it weakens
  attachment access, traceability, and future report generation.

## Consequences

The product has two evidence concepts with clear boundaries:

- implementation evidence proves control implementation records;
- audit evidence documents what was sampled or observed during an audit.

Both use Odoo attachments and company-boundary access controls.
