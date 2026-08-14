# Mission 03 Implementation Plan

## Objective

Build the operational layer connecting reusable Perfect Match framework controls
to client implementations, controlled documents, revisions, and actual evidence.

## Technical Approach

- Extend `pm_qms_core` with `pm.qms.control.instance`.
- Convert `pm_qms_documents` from placeholder to installable addon.
- Add `pm_qms_evidence` as an installable addon depending on core and documents.
- Use Odoo ORM, ACLs, record rules, constraints, chatter, and workflow actions.
- Keep attachments in `ir.attachment`.

## Components Affected

- `addons/pm_qms_core`
- `addons/pm_qms_documents`
- `addons/pm_qms_evidence`
- `deployment/scripts/odoo-dev.sh`
- `docs/`

## Database Changes

New models:

- `pm.qms.control.instance`
- `pm.qms.document`
- `pm.qms.document.revision`
- `pm.qms.evidence`

## Security Implications

QMS User, QMS Manager, and QMS Administrator permissions are extended to the new
models. Company isolation uses record rules. Relationship constraints prevent
cross-company and cross-organization links.

## Testing Strategy

Run:

```bash
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh test-mission03
```

## Acceptance Criteria

- Addons install and upgrade.
- New workflows pass tests.
- Multi-company isolation passes tests.
- No copied external standard text is added.
- Plane is updated by API only.

## Rollback Considerations

The work is on a feature branch. Roll back by stopping the DEV stack and
switching back to the Mission 02 branch or commit.
