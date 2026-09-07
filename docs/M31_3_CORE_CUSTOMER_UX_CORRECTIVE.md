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

Runtime evidence showed that assigning an action to a menu that still owns
children does not make that parent actionable in Odoo 19: it renders as a group
header. The final structure therefore makes `Management Review` a leaf under
Performance, resolving to `pm_qms_management_review.action_pm_qms_management_review`.

The redundant `Reviews` menu keeps its XML ID but is inactive. `Actions`,
`Decisions`, and `Review Inputs` remain direct Performance siblings immediately
after Management Review. Their actions and model security are unchanged.

## Verification

Focused automated tests assert:

- canonical list/form creation is disabled;
- manager model create capability and existing-record write capability remain;
- the guided workflow remains the supported creation path;
- Management Review is an actionable leaf, Reviews remains preserved but inactive,
  and Actions/Decisions/Review Inputs remain Performance siblings;
- no ACL or record-rule files are changed.

The browser contract requires generic Implementation New/Create to be absent and
requires Management Review to be exposed, clickable, and routable through normal
customer navigation. The harness supports span/data-section roots, direct anchor
and button roots, and overflow roots, with bounded discovery and logical-label
deduplication. Disposable runtime UAT, telemetry, responsive checks, and Axe
before/after ownership evidence are required before Product Owner review.

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
