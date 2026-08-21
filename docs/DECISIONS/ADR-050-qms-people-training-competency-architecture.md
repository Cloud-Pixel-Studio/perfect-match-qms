# ADR-050: QMS People, Training and Competency Architecture

## Status

Accepted

## Context

Perfect Match QMS needs to demonstrate personnel competence, training,
qualification validity, and controlled-document awareness. Customers may use
Odoo Employees, another HR platform, or no formal HRIS. A hard dependency on HR
would increase deployment scope and could imply handling sensitive personal data
that is outside the QMS product boundary.

Document awareness must be revision-specific. Acknowledging one controlled
revision cannot satisfy a future revision.

## Decision

Mission 14 introduces `pm_qms_people` as a QMS-native module.

The module defines a lightweight `pm.qms.person` linked to `res.partner` and
optionally `res.users`, scoped by QMS organization and company. It does not
depend on Odoo HR and does not store payroll, medical, banking, immigration, or
other sensitive HRIS data.

QMS roles are configurable records. Role assignments drive competency
requirements and document acknowledgment requirements.

Competency gaps are derived from role competency requirements plus the latest
valid historical assessment. The competency matrix is synchronized from source
records and computes status from real assessments.

Training definitions, training events, and person training records are separate
from competency assessments. Training can support competence, but completion is
not automatically equivalent to competence.

Qualifications compute valid, expiring, expired, or no-expiration states from
dates and configurable expiring-soon windows.

Document acknowledgments are stored against exact `pm.qms.document.revision`
records. New current revisions create new acknowledgment requirements without
mutating historical acknowledgments.

## Consequences

Perfect Match QMS can answer who performs work, which competencies are
required, whether requirements are satisfied, which training is overdue, which
qualifications need attention, and which current document revisions require
acknowledgment.

The product remains a QMS platform rather than an HRIS or LMS. Existing
readiness scoring, evidence records, audit records, and management review
history remain intact.

## Verification

Mission 14 verification includes targeted Odoo tests for people identity,
role-based requirements, competency matrix behavior, training history,
qualification expiration, idempotent reminders, revision-specific
acknowledgments, security boundaries, and dashboard metrics.
