# User Roles, Permissions, and Site Scope

Mission 19 adds a small, explicit role catalog to Perfect Match QMS. Roles are
Odoo `res.groups`; the customer-facing `Configuration > Users & Access` view
only allows these product roles and their scope.

## Roles

| Role | Intended authority |
| --- | --- |
| Quality Manager | QMS-wide management, controlled workflows, review and approval authority within assigned scope. |
| Quality Supervisor | Operational QMS management within assigned scope; inherits the existing QMS manager capabilities for compatibility. |
| Quality Inspector | Read QMS records and create/update assigned operational risk, NCR, and CAPA preparation records; cannot approve or close manager-controlled workflows. |
| Document Controller | Controlled document and revision preparation within assigned scope; document release still uses the document workflow. |
| Internal Auditor | Audit program, audit, scope, criteria, plan, evidence, and finding work within assigned scope; independence checks remain mandatory. |
| Process Owner | Read QMS records for assigned processes and sites; process-specific operational work remains subject to the model ACL and workflow. |
| Management User | Read-oriented QMS visibility for management review and performance context. |
| QMS Viewer | Read-only visibility within explicit scope. |

`QMS User`, `QMS Manager`, and `QMS Administrator` remain technical
compatibility groups for existing modules. Quality Manager is not an Odoo
system administrator and no new product role implies `base.group_system`.

## Scope model

Each QMS user is assigned:

- one or more QMS organizations;
- all sites or an explicit site selection;
- all processes or an explicit process selection.

Selected sites and processes must belong to a selected organization and to a
company allowed for the user. Empty organization scope fails closed. For
process-linked records, an explicitly selected process or a process linked to
an explicitly selected site is required unless the user has the corresponding
all-scope flag.

## Separation of duties

Access to a form or menu never approves a record. Document release, evidence
review, NCR/CAPA closure, CAPA effectiveness, audit independence, management
review decisions, and calibration/OOT disposition continue through their
existing model actions and guards. No `approve_anything` or universal bypass is
introduced.
