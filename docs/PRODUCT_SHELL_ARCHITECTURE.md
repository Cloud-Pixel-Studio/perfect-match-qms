# Product Shell Architecture

Mission 24 hardens `pm_qms_app` as the customer-facing Perfect Match QMS
application boundary. Odoo remains the runtime, ORM, authentication and
authorization framework, menu/action framework, attachment store, scheduler,
and web client.

## Customer information architecture

The product root presents these customer domains:

1. Dashboard
2. Implementation
3. Quality Operations
4. Assurance
5. Performance
6. Action Center
7. Standards
8. Configuration

The grouping reuses existing menu records and actions. It does not create a
second implementation engine, duplicate actions, or change model ownership.

| Root | Existing capabilities |
| --- | --- |
| Dashboard | Executive dashboard and source-driven metrics |
| Implementation | Implementation projects, controls, activities, readiness, and evidence |
| Quality Operations | Risk, NCR, CAPA, customer quality, supplier quality, and equipment/calibration |
| Assurance | Documents, audit, and people/competency |
| Performance | KPI/performance, Cost of Quality, and Management Review |
| Action Center | Cross-functional source-driven actions |
| Standards | ISO 9001 only when the ISO add-on is installed |
| Configuration | Company Profile, Sites, Processes, Users & Access, Commercial License, and Framework Administration |

## Security boundary

Menu visibility is presentation only. ACLs, record rules, action groups, and
workflow authority remain authoritative. Mission 19 and Mission 20 security
was not replaced by menu hiding.

Framework Administration remains restricted to the existing QMS Administrator
group. Technical Administrators retain Odoo Apps, Settings, maintenance, and
troubleshooting surfaces. Normal QMS users do not receive generic Apps,
Project, Tests, or Discuss roots.

Commercial License is under Configuration. Activation Requests is a child of
Commercial License and keeps its Licensing Administrator group. The RC10
effective-view and `activation_request_ids` protections remain unchanged.

## Standards boundary

The ISO 9001 add-on owns Standards navigation and remains the only implemented
standard. Mission 24 changes only its placement order; it does not change ISO
9001 content, controls, mappings, or profiles.

## Mail versus Discuss

Odoo mail infrastructure remains available for `mail.thread`, `mail.activity`,
record chatter, notifications, and audit history. The generic Discuss root is
restricted to Technical Administrators for the customer shell. Communication
records are not deleted and QMS workflow notifications are not replaced.

## Upgradeability

The implementation uses supported addon menu records, inherited QWeb
templates, and SCSS assets. It does not fork Odoo, edit Odoo source, patch
minified vendor assets, or remove legal attribution.
