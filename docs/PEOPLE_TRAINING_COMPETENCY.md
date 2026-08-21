# People, Training and Competency

Mission 14 adds `pm_qms_people`, a QMS-focused people capability for Perfect
Match Digital QMS.

## Architecture

`pm.qms.person` is the QMS person abstraction. It is intentionally lightweight:

- `partner_id` links the business/contact identity.
- `user_id` optionally links an Odoo login.
- `organization_id` and `company_id` preserve QMS scope and company isolation.
- No payroll, attendance, salary, medical, immigration, banking, or disciplinary
  HR data is stored.

The module does not depend on Odoo Employees. Customers can use it with Odoo HR,
without Odoo HR, or with another HR system.

## QMS Roles

`pm.qms.role` defines configurable business/QMS roles such as customer-defined
process roles, quality roles, audit roles, or operational roles. Roles are not
hardcoded.

People receive roles through `pm.qms.person.role.assignment`, which preserves
effective dates, end dates, active status, and history.

## Competency

`pm.qms.competency` defines customer-owned competency definitions. A role can
require competencies through `pm.qms.role.competency.requirement`.

`pm.qms.competency.assessment` records historical assessments. New assessments
do not overwrite previous assessments.

`pm.qms.competency.matrix.line` is synchronized from active role assignments and
role competency requirements. The status is computed from the latest applicable
assessment:

- not assessed
- competent
- gap
- expired
- not required

Gaps are therefore derived from role requirements plus assessment history, not
entered as independent manual statuses.

## Training

Training remains separate from competence:

- `pm.qms.training.course` defines training.
- `pm.qms.training.event` represents a session/event.
- `pm.qms.training.record` preserves a person's training history.
- `pm.qms.training.requirement` can connect training to roles or competencies.

Training completion does not automatically mark a person competent. Competence
is demonstrated by assessment records unless a customer later configures an
approved methodology.

Training records support completion, overdue, expiration, failed/not
satisfactory results, and lightweight effectiveness review fields.

## Qualifications

`pm.qms.qualification.type` defines customer-owned qualification categories.
`pm.qms.qualification.record` stores person qualification history with issuer,
identifier, issue date, expiration date, attachment reference, and derived
status:

- valid
- expiring soon
- expired
- no expiration

The expiring-soon window is configurable per qualification type. Reminder
creation is idempotent and uses Odoo activities.

## Document Revision Acknowledgments

Acknowledgments are revision-specific.

`pm.qms.role.document.requirement` defines which QMS roles must acknowledge a
controlled document. When a current/active revision exists, synchronization
creates `pm.qms.document.acknowledgment` records for each active person-role
assignment.

Acknowledging `Document Rev A` does not acknowledge `Document Rev B`.
Superseded revision acknowledgments remain historical. Synchronization is
idempotent and does not duplicate requirements.

Users linked to QMS people can acknowledge only their own pending records.
Managers and administrators can manage the broader company-scoped set and waive
requirements when justified.

## Integrations

The main Perfect Match QMS dashboard includes Mission 14 attention counts for:

- competency gaps, missing assessments, and expired assessments
- overdue training
- expiring or expired qualifications
- pending document acknowledgments

Document Revision forms show acknowledgment totals: required, completed,
pending, and overdue.

Readiness scoring remains unchanged. Mission 14 records may support evidence
and management review inputs, but they do not change the existing readiness
formula by themselves.

## Security

The module reuses existing groups:

- QMS User
- QMS Manager
- QMS Administrator

QMS users see their linked person records and related personal training,
qualification, matrix, assessment, and acknowledgment records. Managers and
administrators see company-scoped records. Record rules preserve company
boundaries.

## Demo Data

Demo data is optional, fictional, and loaded only through Odoo demo loading. The
production module does not depend on demo records.
