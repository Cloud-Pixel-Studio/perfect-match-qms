# Product Shell Architecture

Mission 22 establishes `pm_qms_app` as the customer-facing Perfect Match QMS
application boundary. Odoo remains the supported runtime, ORM, authentication
framework, security engine, menu/action framework, attachment store, scheduler,
and web client.

When a standard add-on is installed, it contributes only its own customer
surface. The current ISO add-on contributes **Standards > ISO 9001 > Overview**;
no uninstalled or unfinished standards are displayed. Framework master-data
navigation is labeled **Framework Administration** and is under Configuration
for QMS Administrators.

## Boundary

- `pm_qms_app` owns the product root, dashboard entry, identity assets, login
  presentation, and customer navigation.
- Existing QMS addons retain their models, ACLs, record rules, actions, and
  business workflows.
- `base.group_system` remains the technical administration authority.
- Shell presentation never replaces ACLs, record rules, or action security.

## Navigation

Normal QMS users enter through **Perfect Match QMS**. Company Profile, Sites,
Processes, Users & Access, and Commercial License remain under the QMS
Configuration area. Generic Odoo roots such as Apps, Project, Discuss, Tests,
and Settings are reserved for technical administrators by menu groups. The
customer bundle does not add unrelated ERP applications merely to hide them.

Database selection and database management remain deployment concerns. The
customer configuration uses `list_db = False`, a database filter, and
`proxy_mode = True`; these settings do not weaken application permissions.

## Upgradeability and legal identity

The implementation uses supported addon inheritance, QWeb templates, assets,
and menu records. It does not modify or fork Odoo core. Odoo and third-party
notices, licenses, and attribution remain part of the technical distribution.
The product may present Perfect Match QMS as the customer identity while
technical documentation continues to identify Odoo 19 as the runtime.
