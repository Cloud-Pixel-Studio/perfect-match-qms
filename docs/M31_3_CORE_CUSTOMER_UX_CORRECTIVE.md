# M31.3 Core Customer UX Corrective

## Scope

Base: `5eacecfff713ead085aec5650daca5f3063a115c`

This mission addresses the carried customer findings from M31.1/M31.2:

- P1: the canonical Implementation list and form exposed generic creation outside
  the guided New Implementation workflow.
- P2: Management Review was a non-actionable menu container rather than a
  customer navigation destination.

No release, RC12, Demo, production, or customer deployment is part of this
mission.

## Corrective contracts

The canonical Implementation list and form now declare `create="false"`.
Existing records remain readable and editable under existing authority, while
the generator wizard retains its model create capability. ACLs, record rules,
company isolation, license enforcement, and model permissions are unchanged.

The existing Management Review menu keeps its child destinations:

- Reviews
- Actions
- Decisions
- Review Inputs

The parent is also an actionable `Management Review` destination resolving to
`pm_qms_management_review.action_pm_qms_management_review`. This removes the
ambiguous container-only navigation without duplicating the underlying records
or widening access.

## Verification

Focused automated tests assert:

- canonical list/form creation is disabled;
- manager model create capability and existing-record write capability remain;
- the guided workflow remains the supported creation path;
- Management Review has the expected action and preserves all four child menus;
- no ACL or record-rule files are changed.

The browser contract requires generic Implementation New/Create to be absent and
requires Management Review to be exposed, clickable, and routable through normal
customer navigation. Disposable runtime UAT, telemetry, responsive checks, and
Axe before/after ownership evidence are required before Product Owner review.

Expected generation contract:

`37 controls / 20 operational processes / 37 control instances /
118 activities / 111 generated tasks`

Both Sync Framework runs must show zero growth in all four tracked dimensions.

Accessibility findings are classified by evidence as PMQMS-owned, native
Odoo/platform, or mixed/uncertain. No WCAG compliance claim is made. Native
platform findings and unresolved ownership are deferred to M31.4 with their
rule, target, reason, and disposition recorded.

## Security boundary

Expected security-file changes: none. No ACL widening, record-rule widening,
sudo path, model security change, core Odoo change, or customer data mutation is
permitted.

## Cleanup

This is a focused product correction. No RC12 tag, GitHub release, Demo
deployment, production deployment, or real-customer mutation is authorized.
