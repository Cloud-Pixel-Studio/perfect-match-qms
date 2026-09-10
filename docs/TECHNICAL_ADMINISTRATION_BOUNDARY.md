# Technical Administration Boundary

Perfect Match QMS separates customer QMS administration from platform
administration.

## Customer QMS administration

Quality Managers can manage the QMS configuration exposed under the product
shell, including Company Profile, Sites, Processes, Users & Access within the
QMS role model, and the Commercial License view where the existing licensing
contract permits it. Users & Access is explicitly limited to Quality Manager and
QMS Administrator; Technical Administrator platform authority does not grant
that customer action. These surfaces are explicit menu and action allow-lists;
they do not rely on the legacy QMS Manager implication.

Framework Administration is outside the Quality Manager surface. It remains
available only through the established QMS Administrator and Technical
Administrator boundaries. Commercial License remains available to Quality
Manager, Licensing Administrator, and Technical Administrator under its
existing action contract. Activation Requests retain their existing Licensing
Administrator-only boundary.

## Platform administration

System Administrators retain generic Odoo Settings, Apps, technical tests,
Project, Discuss, deployment controls, database operations, scheduled-job
troubleshooting, and other runtime maintenance surfaces through
`base.group_system`. These areas are not customer QMS navigation.

## Enforcement

Menu grouping is only the navigation layer. Configuration actions declare the
same allow-list as their menus, while access is independently enforced by Odoo
groups, ACLs, record rules, and workflow guards. The customer shell delegates
read-only metadata only for the explicit Configuration action XML IDs; it does
not grant a model-wide `ir.actions.act_window` read ACL or action-definition
mutation. The Demo administrator is a separate
technical account and is exempt from named customer-user license consumption;
the seeded Quality Manager is not a System Administrator. Cost Analytics is
restricted to Quality Manager and Management User personas; QMS Viewer does
not receive financial-quality cost records or the Cost of Quality menu.

## Operations

Deployment operators must use the existing secrets mechanism for credentials,
keep database management disabled at the public edge, and never place
passwords, tokens, private keys, or database dumps in Git, project-management
systems, screenshots, or customer documentation.
