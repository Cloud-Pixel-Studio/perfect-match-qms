# M31.1 Customer Browser UAT

This is a disposable, test-only browser harness for the M31.1 baseline. It
must run against a disposable customer instance and never against Demo,
production, `cleanvm-test-02`, or a real customer environment.

## Run

Set `M31_BASE_URL`, `M31_QM_LOGIN`, `M31_QM_PASSWORD_FILE`,
`M31_ADMIN_LOGIN`, and `M31_ADMIN_PASSWORD_FILE`. A restricted Viewer may be
provided with `M31_VIEWER_LOGIN` and `M31_VIEWER_PASSWORD_FILE`.

The password variables contain file paths, not password text. The harness
reads them at runtime and never writes them to reports.

```powershell
$env:M31_BASE_URL = 'http://127.0.0.1:18220'
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
