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

## Client Operational Layer

Risk, NCR, CAPA, and internal audit belong to the client operational layer.
They relate to `pm.qms.control.instance`, documents, evidence, processes, and
organizations. They do not add client implementation data to reusable
`pm.qms.control` definitions.

## Due Dates

Risk, NCR, CAPA, CAPA action, CAPA effectiveness, audits, findings, and finding
follow-up records expose computed overdue indicators and days overdue.
Notifications are intentionally not added yet.
