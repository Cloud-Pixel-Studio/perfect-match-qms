# M27 Security Evidence

## Boundary and non-mutation

M27 hardens authorization boundaries on disposable DEV databases. The branch is
based on `d003ee6f3ab07ebafb6c2bee0ca4d6d3923420b1`; it does not deploy or alter
canonical Demo, customer data, production, RC11, ISO content, or Plane.

The functional changes are the owner/organization rule for transient Viewer
dashboard helpers and the idempotent removal of the former QMS Administrator
implication from the QMS Licensing Administrator group. No production
`sudo()` call site was added by M27.

The affected addon versions are `pm_qms_app` `19.0.1.4.5` and
`pm_qms_license` `19.0.1.0.1`.

## Authorization decisions

- QMS Viewer is read-only for business records and may create only its own
  transient dashboard helper. Dashboard helpers are owner- and
  organization-scoped; Viewer mutation and cross-scope access are denied.
- QMS Administrator has framework-pack master-data authority through the
  existing framework ACLs and Framework Administration menu. It remains
  separate from `base.group_system`; Apps/Settings and Users & Access are
  independently tested boundaries.
- QMS Licensing Administrator retains licensing/activation workflow authority,
  does not inherit QMS Administrator, and is denied framework and user-admin
  surfaces.
- Public/portal QMS access is unsupported in v1.0. The tests cover model access,
  direct IDs, `name_search`, `read_group`, attachments, and message posting.
- Mail threads, activities, chatter, followers, attachments, and workflow
  behavior were not changed by M27.

## Focused fixture and tests

`TestM27Security` creates fictional ORM data in disposable `pmqms_m27_test`:
two companies, two organizations, three sites, two processes, two risks, one
control, one evidence requirement, one control instance, one document, one
evidence record, one binary attachment, one message, and one activity. It
creates public, portal, QMS user, two scoped Viewers, Quality Manager, Quality
Supervisor, QMS Administrator, QMS Licensing Administrator, and Technical
Administrator personas. No fixture data is committed or sent to Demo.

The historical 52/51 runs could not be reconstructed from retained logs or CI
artifacts with their exact commands, tags, collection and skip details. They
are therefore not used to claim an omission. The equivalent current scope was
executed on a fresh database: 61 `pm_qms_app` tests and 15
`pm_qms_license` tests selected, 64 combined tests, 0 failures, 0 errors and
0 skipped tests. The new `TestM27Security` class contains 12 test methods; its
methods are included in the `pm_qms_app` module total and are not double-counted.

The focused evidence-tool suite contains 4 tests and reports 0 failures, 0
errors and 0 skipped tests. Its false-pass regression changes a generated P1
production row to `runtime_covered=NO` and observes `unresolved_p1=1` while
leaving the two genuine deferred P2 rows as `deferred_p2=2`.

Required final commands are:

```text
docker compose -f deployment/docker/dev/compose.yml run --rm odoo-dev odoo -d pmqms_m27_focus_final --init pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_iso9001,pm_qms_migration,pm_qms_people,pm_qms_calibration,pm_qms_license,pm_qms_app,pm_qms_customer_quality,pm_qms_action_center,pm_qms_cost_quality --test-enable --test-tags /pm_qms_app,/pm_qms_license --stop-after-init --without-demo=True --log-level=test
docker compose -f deployment/docker/dev/compose.yml run --rm odoo-dev odoo -d pmqms_m27_focus_final --init pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_iso9001,pm_qms_migration,pm_qms_people,pm_qms_calibration,pm_qms_license,pm_qms_app,pm_qms_customer_quality,pm_qms_action_center,pm_qms_cost_quality --test-enable --test-tags /pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation,/pm_qms_pack_quality,/pm_qms_iso9001,/pm_qms_migration,/pm_qms_people,/pm_qms_calibration,/pm_qms_license,/pm_qms_app,/pm_qms_customer_quality,/pm_qms_action_center,/pm_qms_cost_quality --stop-after-init --without-demo=True --log-level=test
py -3 tools/security/m27_authorization_matrix.py --output <ignored-workspace>/matrix.csv
py -3 tools/security/m27_authorization_matrix.py --output <ignored-workspace>/matrix.csv --validate
py -3 tools/security/m27_sudo_inventory.py --output docs/security/M27_SUDO_REVIEW.csv --validate
```

The focused command reports the combined selected total, while module-level
statistics are not additive. The full command uses the same explicit QMS tags
as `test-mission23`; Odoo/web tests outside that tag set are excluded.

## Runtime authorization matrix

`M27_AUTHORIZATION_MATRIX.csv` inventories 92 declared QMS models plus explicit
surface rows. Runtime statuses are produced only from the `RUNTIME_CASES`
registry in `tools/security/m27_authorization_matrix.py`, which names persona,
operation, scope variant, and exact test method. Static inventory rows are
`REVIEW_REQUIRED`; abstract services are `NOT_APPLICABLE`. `PASS` is not used
for source-only evidence. The generator's validator rejects unsupported
runtime claims and reports total, runtime, static, review, deferred,
not-applicable, and untested P0/P1 counts.

Final regenerated baseline at the corrected evidence branch:

- 2,845 matrix rows;
- 645 runtime rows;
- 2,200 static rows;
- 2,128 `REVIEW_REQUIRED` rows;
- 72 `NOT_APPLICABLE` rows;
- 0 `DEFERRED_M28`, 0 `DEFERRED_M31`;
- 0 P0-sensitive untested rows and 0 P1-sensitive untested rows;
- deterministic SHA-256: `d4cf1e0ff92bf03bd5bc5459a41dc091056bb80bd036ca1a3865e8f16bf69bc5`.

P0/P1 are limited to boundaries with an emitted runtime case; all other
scope-bearing QMS models are explicitly classified P2 operational and remain
review items for M28. This is not a claim of complete tenant-isolation
certification.

## Reports, import, export and actions

No custom QMS `ir.actions.report` was found in the installed addon sources;
custom-report count is zero and therefore `NOT_APPLICABLE`. Native Odoo
import/export and HTTP report behavior is not fully reproducible in the
transaction test harness. The tests cover model ACLs, visible-scope read and
cross-scope exclusion, import-wizard create denial, direct restricted action
IDs, `name_search`, and `read_group`. HTTP/browser-specific export/report
verification is explicitly deferred to M31; it is not recorded as runtime
PASS. Technical Administrator/native platform surfaces are outside the normal
customer persona claim.

## Production sudo review

`M27_SUDO_REVIEW.csv` inventories all 74 `.sudo()` sites under `addons`: 17
production and 57 test-only. Every production row has a specific invoker,
input provenance, user-controlled-input assessment, pre-sudo selection,
company/organization scope, output/mutation behavior, audit/history behavior,
existing regression, risk and follow-up. The 17 sites are unchanged by M27.

Final inventory counts are 17 production, 57 test-only, 15 with direct runtime
regression coverage, 2 specifically static-reviewed/deferred P2 call sites, 0
remediated, 0 unresolved P0, and 0 unresolved P1. The static rows are bounded
configuration or aggregation reads whose domains and outputs are fixed or
pre-scoped; follow-up is recorded per call site. No new production `sudo()`
site was introduced.

## Upgrade rehearsal

The accepted rehearsal is a disposable base-to-head exercise, distinct from
the static `Command.unlink` test. The reproducible pattern is:

1. Create a disposable database named `pmqms_m27_upgrade_<run-id>` from base
   `d003ee6f3ab07ebafb6c2bee0ca4d6d3923420b1`, with the QMS stack installed and
   `pm_qms_app` at `19.0.1.4.4` and `pm_qms_license` at `19.0.1.0.0`.
2. Create fictional licensing-only, QMS-only, and dual-role users through the
   Odoo ORM shell; record company count and role states before update.
3. Point the mounted DEV source to the corrective branch and run both affected
   addon updates:

   ```text
   docker compose -f deployment/docker/dev/compose.yml run --rm odoo-dev odoo -d <db> -u pm_qms_app,pm_qms_license --stop-after-init --without-demo=all
   ```

4. Assert licensing-only loses only the former QMS Administrator implication,
   QMS-only is unchanged, the dual-role user retains both explicit roles, and
   company count remains stable.
5. Run the identical `-u pm_qms_app,pm_qms_license` command a second time and
   assert the same role states, loaded rule/action metadata, and company/user
   counts.
6. Drop only the disposable database using the supported PostgreSQL/container
   command. Do not run the rehearsal against Demo and do not include secrets.

The declarative regression searches for `Command.unlink` and is not a
substitute for this base-to-head rehearsal.

The final rehearsal passed for both affected addons: fresh base install, first
update of `pm_qms_app,pm_qms_license`, and second idempotent update. The first
and second update both reported `pm_qms_app` `19.0.1.4.5` and `pm_qms_license`
`19.0.1.0.1`; the Viewer dashboard rule XMLID count was 1, the Licensing Admin
implication was absent, and company/user counts remained 1/4. The
licensing-only user lost only the former QMS
Administrator implication; the QMS Administrator-only user was unchanged; the
explicit dual-role user kept both roles; company and user counts were stable;
and no business record was created or deleted.

## Static and content boundaries

Addon validation, Python compilation, XML/CSV/JSON validation, `git diff
--check`, secret scanning, and content-safety scanning pass for the current
branch. The final explicit-stack run selected 288 tests and reported 0
failures, 0 errors and 0 skipped tests; it emitted 41 existing/deprecation
warnings. Historical source packages, customer data, credentials, private
keys, Demo data and source-derived datasets are not committed.

## Status

M27 remains incomplete pending exact-head CI and Product Owner merge review.
The current branch head is the exact HEAD reported in the PR checkpoint.
Demo, customer, production, RC11 and Plane remain untouched.
