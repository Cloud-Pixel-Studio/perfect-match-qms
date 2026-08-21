# Perfect Match Activity UX and Project Abstraction

Perfect Match QMS uses Odoo Project as an execution engine, not as the customer-facing implementation workspace.

## Source of Truth
Implementation execution remains backed by:

- `project.project` for the Odoo execution project
- `project.task` for implementation activities

Perfect Match does not create a mirrored task model. There is no `pm.qms.task` model and no task synchronization layer.

## Customer-Facing Activities
The customer-facing activity entry point is:

- `pm_qms_implementation.action_pm_qms_implementation_activities`

That action presents generated QMS tasks as Activities and uses Perfect Match-owned kanban, list, search, and form views. The general action includes only tasks with QMS implementation links. Implementation and control smart buttons add narrower domains so a user sees only the activities for the current implementation context.

## Navigation Rules
Perfect Match navigation should use Perfect Match actions for implementation work:

- Dashboard -> Continue Implementation uses the implementation action.
- Implementation -> Activities uses the Perfect Match Activities action.
- Implementation Control -> Activities uses the Perfect Match Activities action scoped to the control.
- Readiness Center activity recommendations open the Perfect Match Activity form.

Native Odoo Project actions are reserved for users intentionally working in Project.

## Project Launcher Visibility
Perfect Match implementation users inherit Odoo Project groups today because Odoo 19 task ACLs and task workflow behavior live behind those groups. Hiding Project by removing those groups would be a security and behavior change, not a visual-only cleanup.

For Mission 12.1, the supported product abstraction is action/view/context ownership. Project launcher minimization remains technical debt until a dedicated replacement access model is designed and tested.

## Security
Menu hiding is not security. Access remains enforced through Odoo ACLs, record rules, company boundaries, organization-linked QMS records, and the existing Project task security model.

The Perfect Match Activities action includes domains that prevent unrelated generic Project tasks from appearing in QMS implementation screens.

## Validation Expectations
Before release, validate:

- QMS activities are still `project.task` records.
- Perfect Match Activities kanban/list/form views load.
- Generic Project tasks are excluded from Perfect Match activity actions.
- Implementation-specific actions show only that implementation's activities.
- Readiness Center activity actions open the Perfect Match Activity form.
- Native Project still works for administrators and Project-enabled users.
