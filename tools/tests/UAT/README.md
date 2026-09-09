# Customer Browser UAT

This is a disposable, test-only browser harness for M31 customer UAT. The CI
entry point is `deployment/scripts/tests/test_customer_authenticated_uat.sh`;
it provisions through `customer-instance.sh`, generates fictional credentials
and license material ephemerally, and cleans up on exit. It must never run
against Demo, production, `cleanvm-test-02`, or a real customer environment.

## Run

Set `M31_BASE_URL`, `M31_DATABASE`, `M31_ORGANIZATION_NAME`, `M31_QM_LOGIN`,
`M31_QM_PASSWORD_FILE`, `M31_ADMIN_LOGIN`, and `M31_ADMIN_PASSWORD_FILE`. A
restricted Viewer may be provided with `M31_VIEWER_LOGIN` and
`M31_VIEWER_PASSWORD_FILE`.
The CI runner also supplies `M31_AUDITOR_*`, `M31_OWNER_*`, and `M31_API_*`
fixtures for Internal Auditor, Process Owner, and API Integration
Administrator sessions. These values are generated only in the disposable
runner and are never printed or persisted as artifacts.

`M31_ORGANIZATION_NAME` is required and must exactly match the operational
organization created by `bootstrap-customer`. The harness does not select an
organization by partial text or by position.

The password variables contain file paths, not password text. The harness
reads them at runtime and never writes them to reports.

```powershell
$env:M31_BASE_URL = 'http://127.0.0.1:18220'
$env:M31_DATABASE = 'pmqms_m31_uat_test'
$env:M31_ORGANIZATION_NAME = 'Example Customer, Inc.'
$env:M31_QM_LOGIN = 'quality.manager@example.invalid'
$env:M31_QM_PASSWORD_FILE = 'C:\path\to\qm-password.txt'
$env:M31_ADMIN_LOGIN = 'admin'
$env:M31_ADMIN_PASSWORD_FILE = 'C:\path\to\admin-password.txt'
npm ci
npm test
```

Generated reports and screenshots belong in the local `evidence/` directory,
which is excluded by the adjacent `.gitignore`. Do not commit credentials,
session state, customer data, or screenshots containing secrets. This harness
is test tooling only and is not part of any Odoo customer bundle.

## Coverage accounting

The authenticated run records a role matrix and an experience matrix in
Playwright annotations. `TESTED/PASS` means the named behavior was exercised;
`TESTED/FAIL` is a real observed failure; `NOT_TESTED` is intentionally not
claimed as coverage; and `NOT_EXPOSED` records a role-appropriate unavailable
surface. The current matrix covers login (logout is not tested), customer root
navigation, guided implementation, empty states, direct URL restrictions,
dialogs, accessible names/labels, visible focus checks, desktop and constrained
viewports, and each discovered business-domain route. Breadcrumbs, reminders,
chatter, notification links/duplication/recipient isolation, SMTP delivery,
keyboard traversal, required-field errors, overdue behavior, and device/session
IP require a later focused mission. Quality Manager Configuration, including
Company Profile, Sites, Processes, and Commercial License, is normative and is
asserted as reachable; absence is reported as a product finding rather than
reclassified as expected protection.
