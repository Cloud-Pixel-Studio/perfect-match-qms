# ADR-063: Mission 24 Product Shell Navigation and Branding

Status: Proposed

## Context

The RC10 product surface was functionally complete but exposed too many
independent top-level QMS entries. The customer shell also inherited a strong
default Odoo visual treatment even though approved Perfect Match assets and
colors already existed.

## Decision

Use `pm_qms_app` as the presentation boundary for a grouped customer shell.
Reparent existing menu records into Dashboard, Implementation, Quality
Operations, Assurance, Performance, Action Center, Standards, and
Configuration. Keep the XML IDs and actions owned by their existing addons.

Use the existing Perfect Match icon, company mark, and SCSS asset as the
identity source. Add a small token layer and explicit navigation states through
supported addon assets and inherited templates.

Keep Odoo mail infrastructure and record chatter. Restrict the generic Discuss
root for normal customer QMS roles as an existing technical-surface boundary.
Do not edit Odoo core, remove legal attribution, or use menu visibility as a
security mechanism.

## Consequences

- Customer navigation is shorter and organized by QMS domain.
- Commercial License is Configuration > Commercial License, with Activation
  Requests beneath it for the Licensing Administrator.
- Framework Administration remains Configuration-only for QMS Administrators.
- ISO 9001 remains the only displayed standard when its add-on is installed.
- Existing models, actions, ACLs, record rules, mail infrastructure, and
  technical-admin surfaces remain the authority.

## Validation

The change requires menu hierarchy tests, shell asset checks, Mission 19/20
security regression, full addon validation, responsive visual inspection, and
Demo validation after an explicitly authorized merge.
