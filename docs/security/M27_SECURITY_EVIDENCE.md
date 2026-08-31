# M27 Security Evidence

## Scope

M27 hardens authorization boundaries on disposable DEV databases. The branch
is based on main `d003ee6f3ab07ebafb6c2bee0ca4d6d3923420b1`; it does not deploy
or alter the canonical Demo, customer data, RC11, ISO content, or Plane.

The functional changes are the viewer dashboard organization rule and the
idempotent removal of the former QMS Administrator implication from the QMS
Licensing Administrator group. No production `sudo()` call site was added or
changed.

## Authorization decisions

- QMS Viewer remains read-only for business records and transient dashboard
  helpers. Dashboard helpers are owner-isolated and organization-scoped.
- Cross-company and cross-organization direct-record reads are denied by the
  existing company and Mission 19 scope rules.
- QMS Licensing Administrator no longer inherits QMS Administrator. The XML
  update uses `Command.unlink` for only that former implication; it does not
  clear unrelated implications. Licensing retains its own workflow authority.
- Portal/public QMS access is unsupported in v1.0; the test proves no model,
  direct-ID, attachment, or message-post side channel is available.
- Mail threads, activities, chatter, followers, attachments, and workflow
  behavior were not changed by M27.

## DEV fixture

`TestM27Security` creates fictional ORM data in disposable `pmqms_m27_test`:
two companies, two organizations, three sites, two processes, two risks, one
control, one evidence requirement, one control instance, one document, one
evidence record, one binary attachment, one message, and one activity. It
creates public, portal, QMS user, two scoped Viewers, Quality Manager, Quality
Supervisor, QMS Administrator, QMS Licensing Administrator, and Technical
Administrator personas. No fixture data is committed or sent to Demo.

## Commands and results

The remote DEV source was aligned to corrective branch head `d73bf7e` and the
tests ran against disposable databases only. `--without-demo=True` was used.

Focused command:

```text
docker exec pmqms-odoo-dev /entrypoint.sh odoo -d pmqms_m27_test -u pm_qms_app,pm_qms_license --test-enable --test-tags /pm_qms_app,/pm_qms_license --stop-after-init --without-demo=True --log-level=test --http-port 18079
```

Result: **61 tests, 0 failed, 0 errors**. The M27 class contributes 10 test
methods. Odoo's per-module statistics are not additive to the final selected
test total.

The exact historical commands that produced the earlier reported 52-test and
51-test counts were not recoverable from the repository, CI artifacts, or
retained DEV logs. They are therefore not attributed to a particular omitted
test. Equivalent current scope checks were run separately:

```text
docker exec pmqms-odoo-dev /entrypoint.sh odoo -d pmqms_m27_test -u pm_qms_app --test-enable --test-tags /pm_qms_app --stop-after-init --without-demo=True --log-level=test --http-port 18079
```

Result: **49 tests, 0 failed, 0 errors**.

```text
docker exec pmqms-odoo-dev /entrypoint.sh odoo -d pmqms_m27_test -u pm_qms_license --test-enable --test-tags /pm_qms_license --stop-after-init --without-demo=True --log-level=test --http-port 18079
```

Result: **12 tests, 0 failed, 0 errors**. The combined current scope selects
61 tests; the separate runs demonstrate that the total varies with module/tag
selection and that no current regression is omitted or failing. The historical
51 versus 52 discrepancy remains unproven rather than guessed.

Full QMS command:

```text
docker exec pmqms-odoo-dev /entrypoint.sh odoo -d pmqms_m27_full --init pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_iso9001,pm_qms_migration,pm_qms_people,pm_qms_calibration,pm_qms_license,pm_qms_app,pm_qms_customer_quality,pm_qms_action_center,pm_qms_cost_quality --test-enable --test-tags /pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation,/pm_qms_pack_quality,/pm_qms_iso9001,/pm_qms_migration,/pm_qms_people,/pm_qms_calibration,/pm_qms_license,/pm_qms_app,/pm_qms_customer_quality,/pm_qms_action_center,/pm_qms_cost_quality --stop-after-init --without-demo=True --log-level=test --http-port 18079
```

Result: **286 tests, 0 failed, 0 errors**. An earlier unfiltered disposable
attempt selected Odoo/web tests and was stopped; it is not part of this QMS
result.

Upgrade rehearsal on disposable `pmqms_m27_upgrade` used ORM shell commands:

- Before update on main, a licensing-only user also had QMS Administrator;
  QMS-only and dual-role fixtures had their expected groups.
- After `pm_qms_license` update from the corrective branch, licensing-only had
  licensing access and no QMS Administrator; QMS-only remained unchanged; the
  dual-role fixture retained both explicit roles.
- A second identical module update produced the same group state. Company
  count remained `1` throughout. No raw SQL and no Demo database were used.

Static validation passed: Python compilation, XML parsing through module
loading, addon validation, `git diff --check`, local secret scan, and content
safety scan.

## Authorization matrix

`M27_AUTHORIZATION_MATRIX.csv` is a deterministic source inventory of 92
declared QMS models, 3,312 persona/operation rows, and no customer data.
Public/portal rows are runtime-denied by the all-model test. Direct runtime
coverage protects the critical risk, document, evidence, dashboard, license,
activation-request, and framework-pack surfaces. Other concrete models remain
explicitly `REVIEW_REQUIRED` in the inventory until a model-specific fixture
exists; abstract models are `NOT_APPLICABLE`. No P0/P1 critical surface is
left untested by the M27 scope.

The inventory is reproducible with:

```text
py -3 tools/security/m27_authorization_matrix.py --output <ignored-workspace>/M27_AUTHORIZATION_MATRIX.csv
```

Two runs produced the same SHA-256:
`6554257a9ad89265fc23db8697641add82b744542ccd21b5a3d1528cb8328ed1`.

## Sudo inventory

[`M27_SUDO_REVIEW.csv`](M27_SUDO_REVIEW.csv) inventories all **73** `.sudo()`
sites under `addons`: **17 production** sites and **56 test-only** fixture or
assertion sites. The production rows include the exact file, line, callable,
purpose, scope boundary, mutation/read classification, and review status.
M27 added **0 production sudo sites**. The 17 existing production sites are
static P2 follow-up items; none is a new M27 privilege or a confirmed P0/P1
finding.

## Status

M27 remains pending PR CI, Product Owner review, and merge authorization.
Demo remains untouched and no release or Plane update is authorized here.
