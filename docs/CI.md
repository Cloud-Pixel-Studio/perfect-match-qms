# CI Quality Gate

Mission 04 added a lightweight GitHub Actions workflow at
`.github/workflows/qms-ci.yml`.

Mission 10 updates that workflow so the Odoo quality gate runs the complete
Mission 10 addon set, including `pm_qms_pack_quality` and
`pm_qms_migration`, and checks for obvious external-standard content mistakes
before running Odoo tests.

The repository currently has no Git remote configured on the VM, so the workflow
is present locally and will activate after the branch is pushed to GitHub.

## Checks

The workflow runs:

- Python syntax compilation for addons and deployment scripts.
- Odoo addon manifest and XML validation through
  `deployment/scripts/validate-addons.py`.
- High-confidence secret scanning through `deployment/scripts/secret-scan.py`.
- External-standard content safety scanning through
  `deployment/scripts/qms-content-safety.py`.
- Docker Compose configuration validation.
- Odoo Mission 10 tests through `deployment/scripts/odoo-dev.sh test-mission10`.

The CI does not require a project-management database. GitHub Actions is the
authoritative record for CI results; governance checks also ensure retired
Plane integration is not reintroduced into active tooling.

## Local Equivalent

```bash
python3 -m compileall addons deployment/scripts
python3 deployment/scripts/validate-addons.py
python3 deployment/scripts/secret-scan.py
python3 deployment/scripts/qms-content-safety.py
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh test-mission10
```
