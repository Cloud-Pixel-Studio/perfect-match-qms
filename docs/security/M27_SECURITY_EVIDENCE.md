# M27 Security Evidence

## Scope

M27 hardens authorization boundaries on a disposable DEV test database. The
branch is based on main `d003ee6f3ab07ebafb6c2bee0ca4d6d3923420b1` and does not
deploy or alter the canonical Demo, customer data, RC11, or ISO content.

The implementation commits are `807ceb385086f5f620b4cc47873efd0e206f8835`,
`c67526dd0c2b2ec944cf2399d9017f3ceaafa73b`, and
`f73524cd67490a42118cadfb405c54f474d2a0b9`.

## Authorization decisions

- QMS Viewer remains read-only for business records and dashboard transient
  helpers.
- Cross-company and cross-organization direct-record reads are denied by the
  existing company and Mission 19 scope rules.
- QMS Licensing Administrator no longer inherits QMS Administrator. It keeps
  license workflow access but cannot write framework master data or users.
- Portal/public QMS access is unsupported in v1.0; no custom QMS controller was
  found.
- Mail threads, activities, chatter, followers, attachments and workflow
  behavior were not changed by M27.

## DEV fixture

The fixture creates two fictional companies, two organizations, two processes,
two risks, and scoped users for QMS Viewer, Quality Manager, Quality
Supervisor, and QMS Licensing Administrator. It uses ORM test setup only in
disposable `pmqms_test`; it is never a Demo seed and is not committed as data.

## Commands and results

The persistent DEV container was aligned to the branch head and `pm_qms_app`
and `pm_qms_license` were updated in `pmqms_dev` with the Odoo entrypoint.

Focused command:

```text
docker exec pmqms-postgres-dev dropdb -U odoo --if-exists pmqms_test
docker exec pmqms-odoo-dev /entrypoint.sh odoo -d pmqms_test --init <modules.txt contents> --test-enable --test-tags /pm_qms_app,/pm_qms_license --stop-after-init --without-demo=all --log-level=test --http-port 18079
```

Result: 55 tests, 0 failed, 0 errors. The M27 security class contributed five
executed test methods.

Full command:

```text
docker exec pmqms-postgres-dev dropdb -U odoo --if-exists pmqms_test
docker exec pmqms-odoo-dev /entrypoint.sh odoo -d pmqms_test --init <modules.txt contents> --test-enable --test-tags <all module tags from modules.txt> --stop-after-init --without-demo=all --log-level=test --http-port 18079
```

Result: 280 tests, 0 failed, 0 errors. A pre-existing docutils warning
(`Unexpected indentation`) was emitted by an existing content check; the Odoo
test result remained 0 failures and 0 errors.

Static validation passed: addon validation, Python compilation, `git diff
--check`, secret scan, and content-safety scan.

## Sudo inventory

[`M27_SUDO_REVIEW.csv`](M27_SUDO_REVIEW.csv) inventories all 61 `.sudo()` call
sites currently present under `addons`. Test-only setup/assertion calls are
marked `scope_safe_and_regression_covered`. Production call sites are
conservatively marked `justified_but_missing_regression_evidence` for future
call-site-specific review; M27 added no sudo call.

## Residual review

No confirmed P0 or P1 authorization finding remains from the M27 scope tested
above. The conservative production sudo inventory is a P2 follow-up review,
not a claim that every call site has been proven safe under every future
workflow. M27 remains pending PR CI, Product Owner review, and merge
authorization.
