# ADR-079: Quality Manager Configuration Access Contract

Status: Accepted

## Context

The customer shell documents Configuration as the entry point for Company
Profile, Sites, Processes, Users & Access, and the permitted Commercial License
surface. The root and several child actions previously depended on the legacy
QMS Manager implication or had no action-level allow-list. That made the
documented Quality Manager contract unreliable in a browser session and left
menu, action, and ORM checks difficult to distinguish.

## Decision

`pm_qms_app` owns the customer-shell access contract through supported Odoo
`ir.ui.menu` and `ir.actions.act_window` records. Configuration root and the
Company Profile, Sites, and Processes surfaces explicitly allow:

- Quality Manager;
- the existing QMS Administrator compatibility boundary; and
- Technical Administrator.

Users & Access has a separate explicit action and menu allow-list for Quality
Manager and QMS Administrator only. Technical Administrator retains generic
Odoo platform administration, but that does not grant the customer Users &
Access action. Commercial License keeps its existing Quality Manager, Licensing
Administrator, and Technical Administrator action boundary. Activation Requests
remain Licensing Administrator-only. Framework Administration remains outside
the Quality Manager surface and is explicitly limited to the established QMS
Administrator and Technical Administrator boundaries.

No group implication, broad technical role, model ACL, record rule, Odoo core
code, or customer data is changed by this contract. The Quality Manager uses
the existing scoped ORM permissions. Other customer roles retain their current
read or operational permissions but do not receive Configuration navigation or
these direct action contracts; Quality Supervisor compatibility permissions are
not expanded.

## Consequences

Menu visibility, action allow-lists, and underlying ORM permissions can be
validated independently. Direct action metadata is explicit and reviewable,
while record access still depends on ACLs and record rules. Future customer
configuration additions must declare both menu and action groups and add
positive and negative role tests.
