# Technical Administration Boundary

Perfect Match QMS separates customer QMS administration from platform
administration.

## Customer QMS administration

Quality Managers can manage the QMS configuration exposed under the product
shell, including Company Profile, Sites, Processes, users and access within
the QMS role model, and the commercial license view or activation workflow
where their role permits it.

## Platform administration

System Administrators retain generic Odoo Settings, Apps, technical tests,
Project, Discuss, deployment controls, database operations, scheduled-job
troubleshooting, and other runtime maintenance surfaces through
`base.group_system`. These areas are not customer QMS navigation.

## Enforcement

Menu grouping is only the navigation layer. Access is enforced by Odoo groups,
ACLs, record rules, and action security. The Demo administrator is a separate
technical account and is exempt from named customer-user license consumption;
the seeded Quality Manager is not a System Administrator.

## Operations

Deployment operators must use the existing secrets mechanism for credentials,
keep database management disabled at the public edge, and never place
passwords, tokens, private keys, or database dumps in Git, Plane, screenshots,
or customer documentation.
