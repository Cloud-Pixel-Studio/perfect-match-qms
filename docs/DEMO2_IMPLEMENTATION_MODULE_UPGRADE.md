# Demo2 implementation-code deployment (no module upgrade)

The PR changes only Python behavior in `pm_qms_implementation`: the wizard's
pack selector domain and a model constraint rejecting draft packs. It adds no
fields, schema changes, manifest data, XML, access-control data, or migrations.
Therefore Demo2 must load the new Python code by recreating only its Odoo
service. Do **not** run `-u`/`--update pm_qms_implementation` for this change.

## Why a module upgrade is unsafe

An isolated restore of the preserved Demo2 backup showed that Odoo's
`--update pm_qms_implementation --stop-after-init` does not behave as a
single-module data boundary. Its loader read data files across the 61-module
registry graph. In particular, it executed
`pm_qms_pack_quality/data/quality_guided_readiness_data.xml`, whose
`pm_qms_seed_quality_guided_readiness` function updates existing quality
records and calls `action_sync_framework()` for an existing implementation
project. That sync updates project/task/control audit fields, changes
`last_sync_date`, and records a new `pm_qms_event`. Replaying Odoo XML also
executes explicit many-to-many clear-and-create commands in
`pm_qms_implementation/views/project_task_views.xml`.

Consequently, a targeted `-u` can mutate pre-existing QMS history through
dependent-module data functions and can recreate technical view relations.
Those effects are not appropriate for a Python-only change. The add-on's own
manifest having no hooks or migration scripts does not prevent effects from
XML functions in dependent modules.

The record/field comparison of the isolated backup rehearsal contained 1,198
changed entries. The complete redacted JSONL, including every row ID and
before/after value, is retained outside Git with the rehearsal evidence. The
changes grouped as follows:

| Records/fields | Observed effect | Source/evidence |
| --- | --- | --- |
| 1 `pm_qms_event` row (ID 129) | New `Framework synchronized: PM-IMP-00002` event, linked to project 2, company 1, organization 3; prior/new state both `generated`. | XML function in `pm_qms_pack_quality/data/quality_guided_readiness_data.xml` -> `pm_qms_seed_quality_guided_readiness` -> `hooks.seed_quality_guided_readiness` -> `project.sudo().action_sync_framework()`; trace captured this call chain. |
| Project 2 `last_sync_date`, `write_date`, `write_uid`; 37 implementation-control `write_date`/`write_uid`; 74 task `write_date`/`write_uid` | Existing project's last-sync marker and audit metadata changed; business fields on controls/tasks did not. | Same `action_sync_framework()` path; its implementation writes `last_sync_date` and emits the event. This is an actual QMS audit/history mutation, not dismissed as harmless. |
| 37 controls, 37 pack-control lines, 6 framework areas | Only `write_date` changed; substantive field values were equal. | `seed_quality_guided_readiness()` explicitly calls `write()` on the matching control, area and pack-line records on every XML replay. |
| 4 cost-type rows (IDs 1-4) | Only audit `write_date` changed; names/codes remained the four standard PM-CQT types. | `pm_qms_cost_quality/data/cost_type_data.xml` is ordinary manifest data and is replayed by the module-loading graph. |
| 6 `ir_act_window_view` rows (IDs 110-115 removed; 116-121 recreated) | Same two actions (IDs 265/266) retain the same kanban/list/form view IDs (796/797/798), but relation row IDs and timestamps changed. Two other relation rows only had `write_date` refreshed. | The two `view_ids` expressions in `pm_qms_implementation/views/project_task_views.xml` start with the destructive `(5, 0, 0)` clear command, then create the three relations. |
| 270 `ir_model_access`, 94 `ir_rule`, 3 `res_groups`, 4 `ir_sequence` rows | Only audit `write_date` changed; their permission/sequence values were unchanged. | The target manifest replays `security/ir.model.access.csv`, `security/security.xml` and `data/sequence_data.xml`. |
| 89 `ir_ui_view`, 68 `ir_ui_menu` rows | Only `write_date` changed; view/menu definitions and links were unchanged. | Target manifest replays its declared view XML and `views/menu_views.xml`. |
| 343 `ir_module_module.write_date`; 2 stored `menus_by_module` values | Module metadata timestamps refreshed. The stored menu summaries for IDs 420 (`pm_qms_implementation`) and 427 (`pm_qms_pack_quality`) changed to reflect their current menu paths; their underlying menu records were not deleted. | Odoo defines `menus_by_module` as stored computed metadata based on menu paths. The exact trigger for the 343 timestamp refreshes was not isolated; they are retained as unexplained technical side effects, not treated as harmless. |
| 1 `ir_attachment` row (ID 22) | Its `write_date` changed. It is `web_icon_data` for menu 116; no attachment content field changed. | The relation to the menu is verified, but the exact initiating write was not isolated. It remains a technical side effect, not treated as proven harmless. |

All changed fields and exact before/after values—including timestamp values—are
in the row-level artifact. No changed cost, project, task, control, framework
pack, group, rule, access, sequence, view, or menu business value was silently
filtered from that comparison. The new event, project sync timestamp, audit
metadata writes, and relation-row replacement remain classified as side
effects of `--update`; they are the reason the module upgrade is not used for
this Python-only PR.

On a fresh restore of the same backup, a registry startup with the PR code but
without `--update` produced zero record/field differences against the baseline
in the same comparison set. The 2026 pack remained draft and had no linked
implementation project. The mapping profile was already `active` in the backup
and remained unchanged; this procedure does not alter its state.

## Supported command

`deploy-implementation-code-demo2` is deliberately limited to the approved
Demo2 identity: instance `demo2`, database `pmqms_demo2`, Compose project
`pmqms-demo2`, its dedicated volumes/network, and ports 8171/8174. It requires
the already-running Demo2 Odoo service, healthy PostgreSQL, locked runtime,
and `pm_qms_implementation` installed with demo data disabled. It then runs
only:

```bash
PMQMS_DEMO_INSTANCE=demo2 ./deployment/scripts/odoo-demo.sh deploy-implementation-code-demo2
```

The launcher uses Compose to force-recreate only `odoo-demo`, without
dependencies. It checks that the PostgreSQL container identity remains
unchanged and healthy and that Odoo is running afterward. It does not call
Odoo with `--update`, replay XML, execute seeds, initialize modules, import a
license, or touch the database directly beyond a read-only module-state
precondition.

This path is valid only for code-only changes with no schema or XML data
changes. Any future manifest, field, ACL, rule, sequence, view, menu, data,
hook, or migration change requires a separately reviewed database-upgrade
plan and a fresh isolated rehearsal.

## Regression evidence

The launcher regression test verifies the exact Demo2 guards, the installed
module/demo-data precondition, Odoo-only recreation, unchanged PostgreSQL
identity, failure behavior, and absence of module-upgrade, seed, or licensing
commands. The release rehearsal additionally restores the approved backup
into a unique, unpublished test database and compares records and fields
before and after an Odoo startup without `--update`. The test backup and its
record-level comparison are not stored in Git.
