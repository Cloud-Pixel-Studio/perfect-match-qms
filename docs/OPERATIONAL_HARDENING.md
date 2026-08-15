# Operational Hardening

Mission 04 adds the first operational improvement layer for Perfect Match
Digital QMS.

## Auditability

Critical workflow transitions use Odoo chatter tracking and a lightweight
`pm.qms.event` log. The event log stores the acting user, timestamp, previous
state, new state, decision, reviewer or approver where relevant, and notes when
useful.

This is not event sourcing and does not claim cryptographic immutability. It is
an Odoo-native operational history that supports review and troubleshooting.

## Operational Identifiers

Operational records use Odoo sequences:

- Risk and opportunity: `PM-RISK-00001`
- Nonconformity: `PM-NCR-00001`
- CAPA: `PM-CAPA-00001`
- Audit program: `PM-AUDPROG-00001`
- Audit: `PM-AUD-00001`
- Audit finding: `PM-AUDF-00001`
- Objective: `PM-OBJ-00001`
- KPI: `PM-KPI-00001`

## Client Operational Layer

Risk, NCR, CAPA, internal audit, objectives, KPIs, customer performance,
supplier performance, and management reviews belong to the client operational
layer. They relate to `pm.qms.control.instance`, documents, evidence,
processes, partners, and organizations where appropriate. They do not add
client implementation data to reusable `pm.qms.control` definitions.

## Due Dates

Risk, NCR, CAPA, CAPA action, CAPA effectiveness, audits, findings, and finding
follow-up records expose computed overdue indicators and days overdue. Mission
06 adds overdue indicators for objective target dates and KPI measurement
schedules. Notifications are intentionally not added yet.

## Performance Snapshots

KPI measurements preserve target, warning, and direction snapshots at the time
the result is recorded. This protects historical performance evidence when KPI
targets are changed later.

Supplier evaluation scores preserve the weights used on the evaluation record.
Future configuration may centralize default weights, but Mission 06 keeps the
mechanism explicit and reviewable.

## Management Review Snapshots

Management reviews preserve what management reviewed by storing normalized
inputs in `pm.qms.management.review.input`. The snapshot generator collects
operational records through controlled Odoo ORM domains for the selected
company, organization, and period.

Draft and preparing reviews may regenerate system-generated inputs. Manual
inputs are preserved during regeneration. Ready, in-progress, and completed
reviews are locked against normal snapshot regeneration, and completed review
history requires administrative correction authority.

Management review actions are separate follow-up records. Completing a meeting
does not require closing every action, and action verification remains a later
manager-controlled workflow step.
