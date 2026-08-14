# pm_qms_evidence

`pm_qms_evidence` adds actual evidence records for client implementations.

## Scope

- `pm.qms.evidence`: actual client evidence tied to a control instance.
- Evidence can link to an evidence requirement, controlled documents, and Odoo
  attachments.
- Review workflow supports draft, submitted, under review, accepted, rejected,
  and expired states.
- Control instances expose required, accepted, and missing evidence counts.

## Distinction

`pm.qms.evidence.requirement` defines what evidence is expected in reusable
Perfect Match methodology.

`pm.qms.evidence` records what a specific organization submitted for a specific
control instance.

## Security

QMS Users can submit evidence within their company. QMS Managers review,
accept, reject, and expire evidence. Company record rules isolate evidence.
