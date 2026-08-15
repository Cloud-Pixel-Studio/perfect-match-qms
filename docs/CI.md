# CI Quality Gate

Mission 04 added a lightweight GitHub Actions workflow at
`.github/workflows/qms-ci.yml`.

Mission 05 updates that workflow so the Odoo quality gate runs the complete
Mission 05 addon set, including `pm_qms_audit`.

The repository currently has no Git remote configured on the VM, so the workflow
is present locally and will activate after the branch is pushed to GitHub.

## Checks

The workflow runs:

- Python syntax compilation for addons and deployment scripts.
- Odoo addon manifest and XML validation through
  `deployment/scripts/validate-addons.py`.
- High-confidence secret scanning through `deployment/scripts/secret-scan.py`.
- Docker Compose configuration validation.
- Odoo Mission 05 tests through `deployment/scripts/odoo-dev.sh test-mission05`.

The CI does not require Plane database access and does not write to Plane. Plane
updates remain API-only operational actions outside the CI job.

## Local Equivalent

```bash
python3 -m compileall addons deployment/scripts
python3 deployment/scripts/validate-addons.py
python3 deployment/scripts/secret-scan.py
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh test-mission05
```
