# Mission 22 CP1: Current Product Surface

Discovery baseline: `v1.0.0-rc8` / `ff9342eab8f4de679fd6be7e17753951a0536b99`.

## Runtime Inventory

The canonical Demo database is `pmqms_demo`. The QMS shell is owned by
`pm_qms_app`, which extends the root menu declared by `pm_qms_core` and uses
the approved Perfect Match icon and logo in `pm_qms_app/static/description/`.
The Demo runtime is configured with `list_db = False`, a database filter for
the Demo database, and `proxy_mode = True`. These settings are deployment
configuration, not a replacement for application security.

## Root Menu Findings

The current Odoo root surface contains:

| Root menu | XML ID | Current visibility | Mission 22 decision |
| --- | --- | --- | --- |
| Perfect Match QMS | `pm_qms_core.menu_pm_qms_root` | QMS User / QMS Viewer | Keep as the primary product entry |
| Discuss | `mail.menu_root_discuss` | Role / User | Technical-admin navigation only; preserve mail/chatter infrastructure |
| To-do | `project_todo.menu_todo_todos` | No group in the optional Demo module | Restrict to technical admins when installed; the clean customer bundle does not depend on `project_todo` |
| Project | `project.menu_main_pm` | User / Administrator | Technical-admin navigation only; QMS implementation actions remain under Perfect Match |
| Apps | `base.menu_management` | No group | Technical-admin navigation only |
| Settings | `base.menu_administration` | Access Rights / Role / Administrator | Keep technical access; do not expose to normal QMS users |
| Tests | `base.menu_tests` | No group | Technical-admin navigation only |

The ungrouped roots are the main customer-facing shell leak. Optional ERP roots
are handled without adding an application dependency: when an optional module
is installed, `pm_qms_app` restricts its known root menu by XML ID; when it is
absent, the customer bundle remains clean. The current
Perfect Match root also contains valid functionality, but the domain is
spread across many technical-sounding children such as Framework, External
Mappings, Operational Events, and Administration / Migration. Those remain
available only according to their existing groups; Mission 22 will not create
duplicate business actions or engines.

## Persona Findings

- Current fictional restricted users are not members of `base.group_system`.
- The Demo `admin` account is currently a System Administrator and is therefore
  a technical account, not a valid Quality Manager persona for Mission 22.
- The existing QMS role groups and Mission 19 scope rules remain the
  authoritative server-side permission model.
- Users & Access and Commercial License already have explicit QMS group
  restrictions; the shell must preserve those restrictions and add no second
  permission engine.

## Required Answers

1. Quality Manager and restricted personas currently receive the QMS surface
   plus the ungrouped `Apps`, `To-do`, `Tests`, and the generic `Project` and
   `Discuss` roots through inherited technical groups.
2. Technical administrators need Settings, Apps, deployment/runtime tools, and
   troubleshooting surfaces; these remain available through
   `base.group_system`.
3. The database selector/manager is disabled by the existing customer
   deployment configuration (`list_db = False`, `dbfilter`), and must remain a
   deployment concern rather than a UI workaround.
4. Company switching is not a customer tenancy mechanism: Mission 21 gives each
   customer one licensed operational company. Existing single-company users do
   not need a new switcher or multi-company implementation.
5. The login and backend branding are partially styled by `pm_qms_app`; the
   next implementation will add supported product identity and the default
   dashboard entry without modifying Odoo core.
6. `pm_qms_app` is the correct shell boundary. A separate branding addon would
   duplicate the existing application boundary, so it is not justified.
7. Menu groups, inherited views, QWeb templates, and the supported backend asset
   bundle can implement the shell. Hidden menus are presentation only; direct
   authorization continues to come from groups, ACLs, record rules, and action
   security.
8. Login, the root navigation, app switcher, configuration entry points,
   denied technical routes, the dashboard, Action Center source links, and
   Cost Analytics require visual regression coverage.
9. Product branding must preserve Odoo and third-party notices, licenses, and
   attribution. The product may be presented as Perfect Match QMS while
   technical documentation accurately states that it runs on Odoo 19.

## Implementation Boundary

Mission 22 will extend `pm_qms_app` only. It will not fork or patch Odoo core,
add a second authorization model, install unrelated ERP applications, or
change the licensing and environment-identity services.
