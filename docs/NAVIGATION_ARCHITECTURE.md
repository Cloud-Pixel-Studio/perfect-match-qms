# Navigation Architecture

Mission 24 groups the existing Perfect Match QMS actions into customer domains
without duplicating business functionality.

## Root groups

| Root | Child placement | Role notes |
| --- | --- | --- |
| Dashboard | Dashboard | QMS users and viewers |
| Implementation | Projects, controls, activities, readiness, evidence | Existing implementation authority |
| Quality Operations | Risk & Improvement, Customer Quality, Supplier Quality, Equipment & Calibration | Existing operational scopes |
| Assurance | Documents, Audit, People & Competency | Existing assurance workflows |
| Performance | Performance, Cost of Quality, Management Review | Existing analytics and review actions |
| Action Center | Unified actions | Intentionally prominent cross-functional entry |
| Standards | ISO 9001 > Overview | ISO add-on owns the standard surface |
| Configuration | Company Profile, Sites, Processes, Users & Access, Commercial License, Framework Administration | Administrative customer configuration |

## Action ownership

Every child entry retains its pre-Mission-24 XML ID and action. The shell only
changes the parent and sequence of the existing menu records. This preserves
breadcrumbs, direct action identity, and module ownership.

## Role visibility

- Quality Manager receives the customer QMS shell, Commercial License, and
  operational configuration intended for that role, but not Framework
  Administration or Activation Requests.
- Quality Supervisor and QMS Viewer receive their existing operational/read
  scope and no privilege escalation through navigation.
- Technical Administrator retains Apps, Settings, maintenance, Framework
  Administration, and Standards > ISO 9001. Commercial License remains denied
  as designed.
- QMS Licensing Administrator retains Activation Requests through the
  Commercial License branch.

Direct URLs remain governed by model ACLs, record rules, and action security.
Hiding a menu never grants access and is not used as an authorization control.

## Standards and framework separation

Standards is a customer-facing entry for installed standard add-ons. Framework
Administration is an administrator-only master-data surface. Normal QMS users
consume generated implementation records, readiness, evidence, and operations;
they do not need to navigate framework internals.
