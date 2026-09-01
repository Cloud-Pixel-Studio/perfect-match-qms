# Security Audit Baseline

## Baseline Identity

- Date: 2026-09-01
- Mission: M29 Security code audit automation
- GitHub Issue: #96
- Base SHA audited for discovery: `5aafc2d14513e8d6c2734a9cdaecddc234dde887`
- Branch: `codex/mission-29-security-audit-automation`
- Enforcement mode: `baseline`

## Scope

The audit covers repository source code, local Odoo addons, deployment scripts,
GitHub Actions workflows, Docker Compose/YAML configuration, dependency inputs,
secret scanning and evidence artifacts. It excludes generated output, caches,
local runtime volumes, secrets, backups, filestore data, licensed-standard
private folders and the historical `plane/` archive.

No customer data, Demo data, production database, migrations or operational
records are modified by this mission.

## Tools And Versions

| Tool | Version | Install / Verification | Status |
| ---- | ------- | ---------------------- | ------ |
| OpenGrep | `v1.29.0` | Official release binary, Linux SHA-256 `3365ef49d04893e01338d85d9bbd49b2bd5261ad4c9c0df0a6a0f8d44232ae13`, Windows SHA-256 `ee485b31912704dc6410bc43f04b5c6ad896697db56e360a98204abf95fa1025` | Added |
| pylint | `4.0.8` | Isolated Python virtualenv | Added |
| pylint-odoo | `10.0.11` | Isolated Python virtualenv | Added |
| Trivy | `0.74.0` | Official release asset, Linux SHA-256 `2ae6fe3ee734b7fdf11335663e18c75ea12dccc76062f09f164a3b0f8be4371a`, Windows SHA-256 `94c40e0696e4b907a74b7b2e1438d5d72ebaca83115817407f568a002d520842` | Added |
| pip-audit | `2.10.1` | Isolated Python virtualenv | Added, requires dependency input |
| PMQMS secret scan | repository script plus masked git history grep | Local only | Reused and extended |
| OWASP ZAP | Not installed by default | Requires disposable local target | Not executed |

## Commands

```bash
bash -n deployment/scripts/security-audit.sh
bash deployment/scripts/security-audit.sh
python3 deployment/scripts/secret-scan.py
python3 deployment/scripts/qms-content-safety.py
python3 deployment/scripts/validate-addons.py
python3 -m unittest tools.security.test_m27_evidence
opengrep scan --validate --config security/opengrep/rules
```

Existing Odoo focused/full regression commands remain the canonical
`deployment/scripts/odoo-dev.sh` targets documented in `docs/TESTING.md` and
`docs/security/M27_SECURITY_EVIDENCE.md`.

## Local Result By Tool

Local validation was run on Windows Git Bash with run id `local-validation`.
The canonical command returned exit code `0` with status `BASELINE`.

| Tool | Result | Count / Evidence |
| ---- | ------ | ---------------- |
| OpenGrep | `EXECUTED` | 81 informational findings: 79 `sudo()` review items and 2 cron inline-code review items. 0 critical, high, medium or low findings. |
| OpenGrep rule tests | `PASS` | 26 positive fixture findings, 0 negative fixture findings, 18 expected rule IDs present. |
| pylint-odoo | `EXECUTED_BASELINE` | 4,624 messages: 3,727 convention, 353 error, 300 warning, 244 refactor. Dominant historical categories are line length, missing docstrings, translations, runtime imports, protected access and duplicate code. |
| Trivy | `EXECUTED` | 0 vulnerabilities, misconfigurations or secrets in repository scan; CycloneDX SBOM generated. |
| pip-audit | `NOT_EXECUTED` | No canonical requirements or Python lockfile exists. |
| PMQMS secret scan | `PASS` | Current-code scan pass; masked git-history scan pass with 0 locations. |
| OWASP ZAP | `NOT_EXECUTED` | No disposable local Odoo target and non-destructive test-account configuration are defined. |
| M27 evidence tools | `PASS` | 4 unit tests pass; sudo inventory reports 17 production-reviewed sites, 61 test-only fixtures, 0 unresolved P0/P1. |

The local command generated these evidence files under
`.security-audit/reports/local-validation/`:

- `opengrep.json`
- `opengrep.sarif`
- `opengrep-rule-tests.json`
- `pylint-odoo.json`
- `trivy.json`
- `trivy.sarif`
- `sbom.cyclonedx.json`
- `pip-audit.json`
- `secret-scan.json`
- `zap.json`
- `summary.json`

The workflow publishes the same files as downloadable artifacts. SARIF upload
is attempted for OpenGrep and Trivy when GitHub code scanning accepts it; JSON
reports remain available either way.

## Severity Policy

- `CRITICAL`: blocks.
- `HIGH`: blocks when confirmed or not covered by an approved baseline.
- `MEDIUM`: reports and requires triage.
- `LOW`: reports.
- `INFO`: optional/reporting.

M29 starts in baseline mode because historical Odoo/pylint findings and
framework-review findings require Product Owner triage before full enforcement.
Scanner infrastructure failures and critical findings still block the command.

## Confirmed Findings

None confirmed. The OpenGrep findings observed locally are review inventory
items already aligned with M27-style sudo/cron review. No Trivy vulnerability,
misconfiguration or secret finding was observed.

## False Positives

None approved. `security/exclusions.yml` contains no active M29 exclusions.

## Accepted Risks

None approved for M29.

## Tools Not Executed

- `pip-audit` reports `NOT_EXECUTED` because no canonical requirements or
  Python lockfile exists. The repository currently has pinned runtime container
  images but no Python dependency input suitable for a reproducible application
  dependency audit.
- OWASP ZAP is `NOT_EXECUTED` until a local throwaway Odoo target, credentials
  through environment variables or GitHub Secrets, and a passive baseline policy
  are defined.

## Limitations

- Full Odoo focused/full regression tests require the Docker-based DEV runtime.
  They were not executed by the security-audit command itself.
- `pylint-odoo` runs from an isolated venv, not inside the Odoo runtime. Import
  findings for `odoo`/runtime-only packages are expected baseline items unless a
  future job supplies Odoo stubs or runs the linter inside an approved isolated
  image.
- OpenGrep rules are conservative review detectors. A `.sudo()` finding is a
  review item, not an automatic vulnerability.
- Trivy downloads its vulnerability database during execution but does not
  upload repository source code.

## SBOM

Trivy generates `sbom.cyclonedx.json` as a CI/local artifact. SBOM files are not
committed.

## Evidence

Primary evidence is the artifact bundle from the Security Audit workflow and
the local `.security-audit/reports/<run-id>/` directory. The PR should include
the run SHA, summary counts and any follow-up issue links.

## Reevaluation Criteria

Re-run the audit after any security-sensitive controller, role, rule, license,
attachment, evidence, deployment, dependency or workflow change. Reevaluate the
baseline before moving `security/policy.yml` from `baseline` to enforcement.
