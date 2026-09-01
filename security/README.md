# Security Audit Automation

SEC-AUDIT-01 provides a local, repeatable security and code-quality baseline
for Perfect Match QMS. Official roadmap M29 has not started. The audit is
intentionally local-first: it uses local OpenGrep rules,
isolated tool downloads, isolated Python virtual environments, and CI
artifacts. It does not upload source code to third-party scanning services.

## Canonical Command

Run from the repository root:

```bash
bash deployment/scripts/security-audit.sh
```

Reports are written under `.security-audit/reports/<run-id>/`, which is ignored
by Git. CI uploads the generated JSON, SARIF and SBOM files as workflow
artifacts.

## Discovery Matrix

| Control | Already Exists | Coverage | Change Needed |
| ------- | -------------: | -------- | ------------- |
| QMS CI quality gate | Yes | `.github/workflows/qms-ci.yml` runs compile, addon/XML validation, secret scan, content safety, compose validation and focused Odoo suites. | Keep gate and pin external actions by SHA. |
| Secret scanning | Yes | `deployment/scripts/secret-scan.py` scans current text files for high-confidence credentials. | Reuse it and add a masked git-history scan in the audit command. |
| Content safety | Yes | `deployment/scripts/qms-content-safety.py` blocks obvious licensed-standard files/text. | Reuse outside the security-audit scanner set. |
| Addon manifest/XML validation | Yes | `deployment/scripts/validate-addons.py` validates local addon manifests, XML and CSV references. | Reuse in existing QMS CI; no duplicate audit scanner. |
| M27 authorization matrix | Yes | `tools/security/m27_authorization_matrix.py` inventories runtime and static authorization claims. | Reference in baseline; do not duplicate M27 runtime tests. |
| M27 sudo inventory | Yes | `tools/security/m27_sudo_inventory.py` reviews production and test-only `.sudo()` call sites. | Reuse as context; OpenGrep adds future-review detection. |
| OpenGrep SAST | No | No existing OpenGrep/Semgrep-compatible scanner. | Add pinned OpenGrep binary install with local PMQMS rules, JSON and SARIF. |
| Odoo quality lint | No | No OCA `pylint-odoo` workflow. | Add pinned `pylint`/`pylint-odoo` in an isolated venv against `addons/pm_qms_*`. |
| Dependency vulnerability audit | Partial | Odoo/PostgreSQL/Alpine runtime images are pinned by digest; no Python requirements or lockfile exists. | Run Trivy for repo/config; classify pip-audit as `NOT_EXECUTED` until Issue #98 supplies a reproducible input. |
| SBOM | No | No CycloneDX artifact is generated. | Add Trivy CycloneDX SBOM artifact. |
| DAST/ZAP | No | No reproducible disposable local target is defined for passive ZAP. | Document as `NOT EXECUTED` until a local target URL and test account flow exist. |

## Tooling Policy

- OpenGrep `v1.29.0` is downloaded from the official GitHub release and
  verified with the release SHA-256 for the Linux or Windows x64 asset.
- Trivy `0.74.0` is downloaded from the official GitHub release and verified
  with the release SHA-256 for the Linux or Windows x64 asset.
- `pylint==4.0.8`, `pylint-odoo==10.0.11` and `pip-audit==2.10.1` are installed
  in `.security-audit/cache/`, never in the Odoo runtime Python.
- OpenGrep uses only repository-local rules in `security/opengrep/rules/`.
- Findings are reported in baseline mode first. Critical findings, untriaged
  pip-audit vulnerabilities and scanner infrastructure failures affect the
  command's exit decision.
- pip-audit states are explicit: `NOT_EXECUTED` (no input), `PASS_NO_FINDINGS`,
  `FINDINGS_UNTRIAGED` (non-zero policy result), and `ERROR/BLOCKED`.
- The baseline reports **0 confirmed P0/P1 from executed OpenGrep, Trivy and
  secret scans**. It does not claim total P0/P1 open is zero before triage.
- 4,624 pylint-odoo messages remain untriaged under Issue #99.

## Exclusions

Approved exclusions must be narrow and recorded in `security/exclusions.yml`.
Inline OpenGrep suppressions must be localized to the exact line and must
reference the matching exclusion record in review notes.

Issues #98, #99 and #100 are SEC-AUDIT-01 follow-ups and possible future M29
candidates. ZAP is `NOT_EXECUTED` under Issue #100. This workstream is a
security baseline, not comprehensive production validation.
