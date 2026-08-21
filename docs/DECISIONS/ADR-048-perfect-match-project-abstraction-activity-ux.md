# ADR-048: Perfect Match Project Abstraction and Activity UX

## Status
Accepted

## Context
Perfect Match QMS implementation execution intentionally uses Odoo `project.project` and `project.task`. Mission 12 visual validation found that some implementation activity paths opened the native Odoo Project task action, causing the user-facing application context to switch from Perfect Match QMS to Project even though the underlying data was correct.

The issue is product context, navigation, and presentation. It is not a data-model problem.

## Decision
Perfect Match QMS keeps `project.task` as the source of truth for implementation activities. It does not introduce `pm.qms.task`, duplicate tasks, or synchronize a second task table.

Implementation activities are exposed through the Perfect Match-owned action `pm_qms_implementation.action_pm_qms_implementation_activities`. That action uses `project.task` with QMS-specific kanban, list, search, and form views. The default domain includes only generated Perfect Match implementation activities, and implementation smart buttons narrow the domain to the selected implementation or control.

Readiness Center activity recommendations and implementation control task buttons must open this Perfect Match action instead of Odoo's native `project.action_view_task`.

The native Project application remains installed and functional for administrators and users who legitimately use Odoo Project. Perfect Match does not globally rename Project or Task and does not modify native Project actions.

## Project Visibility
Odoo 19 exposes the Project launcher through `project.group_project_user`. Perfect Match implementation currently implies that group for QMS users because Odoo's task ACLs, stages, project task record rules, assignments, deadlines, and mail behavior are part of the Project security architecture.

Removing the Project group would break or risk breaking the execution engine unless Perfect Match adds a complete, audited replacement access model for project tasks and project stages. Mission 12.1 therefore avoids hiding Project by removing required permissions. The customer-facing workflow is corrected through Perfect Match actions and menus; launcher minimization can be revisited only with a dedicated security ADR and tests.

## Consequences
Normal QMS work can proceed through Perfect Match QMS -> Implementations -> Activities -> Activity Detail while the underlying records remain Odoo project tasks.

Project-enabled users and administrators retain native Project behavior. QMS-only users may still see Project when they inherit Odoo's Project group for task execution, but they are no longer required to navigate through Project for Perfect Match implementation work.

Future work may evaluate a narrower QMS task security layer, but it must preserve project task create/read/write, stage transitions, followers, deadlines, assignments, company rules, and organization boundaries before Project launcher visibility is changed.
