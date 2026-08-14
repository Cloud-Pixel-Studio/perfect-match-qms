# pm_qms_documents

`pm_qms_documents` adds controlled document identity and revision management for
Perfect Match Digital QMS.

## Scope

- `pm.qms.document`: stable controlled document identity.
- `pm.qms.document.revision`: revision history, approval state, and file link.
- Controlled actions for submit, approve, reject, activate, supersede, obsolete,
  and create new revision.
- Links documents to framework controls and client control instances.

## Storage

Document files are linked through Odoo `ir.attachment`. The addon does not store
duplicate binary fields on custom QMS models.

## Security

QMS Users can read controlled documents. QMS Managers can create, update, and
perform workflow actions. QMS Administrators have full configuration rights.
Company record rules isolate documents and revisions.
