# M31.4-C4.2 PC Recovery Handoff

Status: WIP / PRODUCT ACCEPTANCE BLOCKED. Snapshot: 2026-09-16.
This document preserves work, not a passing certification. No merge is
authorized. Separate Product Owner authorization is required for any merge.
Do not modify Demo, production, real customers, cleanvm-test-02, PR #147,
release tags, RC11, or repository protections. Do not create RC12.

## Authority and Revisions

Repository: `Cloud-Pixel-Studio/perfect-match-qms`.

| Reference | Branch / SHA | Disposition |
| --- | --- | --- |
| Main | `d57ce391cc262c68d5bbe255eb53f448cd7356ff` | Includes merged Configuration contract PR #149 |
| Product PR #150 | `codex/m31-4-c4-scoped-configuration-action-access` / `0d66fd21e5ea1fcdba8e984febed626b835d0442` | OPEN, pending, 10 files +352/-28 |
| Validation PR #151 | `codex/m31-4-c4-1-integration-browser-acceptance` / `952aac60a259c80fbdbc2df4dc245e8e36bb22a3` | DRAFT, pending; revision before this handoff |
| Source PR #147 | `codex/m31-4-c1-1-ephemeral-uat` / `c4f1bdfb287a852cec6ba0e20e465020a5149baf` | OPEN, unchanged |

The handoff commit's final SHA is recorded in PR/issue comments, not in this
document, to avoid a self-reference. Fetch those refs before resuming; stop
and reconcile if other work has advanced them. PR #151 incorporates the
product branch through ordinary merges. Its total base diff contains product
files inherited from #150; they are NOT independently authored validation
changes. Before this document it was 15 files +1531/-51. The new handoff adds
one documentation file. Do not describe all 16 files as harness-only changes.

Issues #148 (product Configuration), #146 (customer UAT), #136 and #122
(parents) remain open. PR #150/#151 refer to #148/#146; never close a parent
as a side effect of this handoff. GitHub is authoritative; Plane is retired.

Mission starting refs were product `c2dd64a95303972029641b245ca04a76c54e9f83`
and validation `eec293aed0d9742344023d6e35148ffb07223083`, on the main above.
The objective remains supported Odoo action authorization plus verified normal
Configuration navigation, with independent direct-action and data/workflow
tests. Product changes belong to #150; harness/evidence changes to #151.

## Required Authorization Contract

These are acceptance requirements, NOT a claim that every runtime cell passed.
Use independently assigned roles, not additional implied groups to make tests
pass. Legacy QMS Manager must receive no new Configuration authority.

| Surface | QM | QMS Admin | Licensing Admin | Technical Admin |
| --- | --- | --- | --- | --- |
| Configuration root | Allow | Allow | Allow | Allow |
| Company Profile / Sites / Processes | Allow | Allow | Deny | Allow |
| Customer Users & Access | Allow | Allow | Deny | Deny |
| Commercial License | Allow | Deny unless separately licensed role | Allow | Allow |
| Activation Requests | Deny | Deny unless separately licensed role | Allow | Deny |
| Framework Administration | Deny | Allow | Deny | Allow |

Quality Supervisor, Internal Auditor, Process Owner, Viewer and API Integration
Administrator have no Configuration access. Technical Administrator retains
native platform administration but not the customer Users & Access action.
Model ACLs, record rules, company isolation, license enforcement and workflow
permissions remain independent boundaries; metadata visibility is not data or
mutation authorization. No broad technical/legacy-manager grant is permitted.

## Durable Findings and Unresolved Work

1. The pinned Odoo browser action route uses a sudoed `_get_action_dict()`.
   Product `addons/pm_qms_app/models/actions.py` checks the authenticated
   request environment for its explicit action allow-list before delegation.
   The map now contains 14 action XML IDs, not the original six. Internal
   superuser behavior and target-model permissions must remain intact. Review
   the actual HTTP path, not only direct ORM `read()` tests.
2. There is one unresolved OpenGrep sudo-review conversation on each of #150
   and #151 at `actions.py:76`. A successful Security workflow does not resolve
   these conversations or constitute approval. Do not suppress the rule.
3. Current product changes prioritize Configuration before Implementation,
   explicitly scope technical children, and place Activation Requests beside
   Commercial License under Configuration. These are pending changes; the
   sibling adjustment has NOT resolved the Licensing Administrator timeout.
4. Latest completed integration run authenticates QM and QMS Administrator,
   enumerates 5 and 15 Configuration entries respectively, and reports those
   two navigation loops PASS. Licensing Administrator authenticates and has a
   reachable direct Configuration root, then stalls between
   `M31_CONFIGURATION_ROOT_OPEN_BEGIN` and its absent END. The 600-second test
   timeout follows. The precise blocking operation is NOT yet isolated.
5. `openRootMenu()` has an unbounded Playwright hover before its click. Latest
   harness uses DOM `node.click()` dispatch; this does not prove ordinary user
   actionability and did not fix the observed timeout. Inspect the role's DOM,
   overlay/geometry and each awaited operation before further product changes.
6. Direct probes use a fixture XML-ID manifest and inspect JSON-RPC responses,
   but still run after navigation in the SAME timed test. After the timeout,
   `browser.newContext` fails because the browser has closed. Required direct
   probes are therefore NOT certified independently. Split the test lifecycle;
   do not report missing probes as denials or successes.
7. Screen-load proof still relies too heavily on action metadata; response
   correlation uses the last observed action response and may race. Protected
   data and workflow results include `NOT_SEPARATELY_PROBED` / `NOT_PROBED`.
   Representative fictional data, prohibited mutation, company isolation and
   action-definition mutation acceptance remain to be completed.
8. QM viewport telemetry at 1600x900, 1280x720 and 1024x720 found Configuration
   visible and an overflow control at narrower widths. QM telemetry reported
   no console/page/request/HTTP errors. This does not certify Licensing Admin
   navigation or all roles at all widths. Do not force-display hidden nodes.
9. Product CI also has a separate failing assertion:
   `TestM314ConfigurationAccess.test_framework_administration_is_outside_quality_manager_surface`.
   It must be investigated, not hidden by changing expectations blindly.
10. Reconcile stale six-action descriptions and sudo-inventory line references
    against the current map during the next focused corrective. Older README
    claims of independent direct tests are superseded by the measured limits
    above. No confirmed data exposure follows merely from a title/menu label.

## Executed Evidence (Not Replaceable by Workflow Links Alone)

| Revision / Run | Result and durable conclusion |
| --- | --- |
| Product `0d66fd2`, [QMS 35016711115](https://github.com/Cloud-Pixel-Studio/perfect-match-qms/actions/runs/35016711115) | FAIL. Mission16: 266 tests, 1 failed, 0 errors; assertion named above. Mission23 skipped. Static, secret/content, proxy, bootstrap, backup/scheduler and runtime-lock steps preceding Mission16 succeeded. |
| Product [Security 35016711407](https://github.com/Cloud-Pixel-Studio/perfect-match-qms/actions/runs/35016711407) | SUCCESS; not product acceptance. |
| Validation `952aac6`, [QMS 35018656070](https://github.com/Cloud-Pixel-Studio/perfect-match-qms/actions/runs/35018656070) | FAIL. Browser suite 10 passed / 1 failed, 12.5 minutes. Licensing root timeout; direct probes cannot finish. Cleanup PASS. Mission16/Mission23 and later gates skipped. |
| Validation [Security 35018656121](https://github.com/Cloud-Pixel-Studio/perfect-match-qms/actions/runs/35018656121) | SUCCESS; unresolved sudo-review remains. |
| Prior validation `cfdf3cf991d9a262853e94cda8be23c856dc82ae`, [QMS 35016719503](https://github.com/Cloud-Pixel-Studio/perfect-match-qms/actions/runs/35016719503) | Same browser symptom, 10 passed / 1 failed; cleanup PASS. Earlier evidence, not current-head certification. |

GitHub pull-request workflows check out synthetic merge refs: product logs
identify `9cda246...` merging `0d66fd2...` into `d57ce391...`; validation logs
identify `e20ed12...` merging `952aac6...` into that main. Record the full actual
checkout SHA from the new run when certifying; never call a PR merge-ref checkout
the identical branch SHA. No full-QMS PASS is claimed for these revisions.

Browser runtime command was
`bash deployment/scripts/tests/test_customer_authenticated_uat.sh`.
Product test command was `bash deployment/scripts/odoo-dev.sh test-mission16`;
the downstream full gate is `bash deployment/scripts/odoo-dev.sh test-mission23`.
Syntax/manifests/XML, secret scan and content safety passed before the UAT
failure. Cleanup log states `authenticated customer UAT cleanup: PASS`; it is
not a claim of independent inspection of a protected host. Raw traces/screenshots
were ephemeral and were not inspected or archived here. Sanitized facts above
survive workflow expiration. New handoff-only CI belongs to its new commit and
must be reported separately in PR comments, never inherited as green.

## Local Inventory and Format Safety

The mission Git repository had exactly two worktrees, product and validation.
Both had no tracked modifications at handoff start. All local branch commits
were reachable from fetched origin refs (`git log --branches --not --remotes`
was empty). Product was clean. Validation contained untracked UAT node_modules,
ignored Python caches and ignored `evidence/playwright.json` / `.last-run.json`.
No pending tracked pnpm lock change exists; no pnpm-lock.yaml was found in the
mission checkouts or inspected historical workspace. Keep npm/package-lock;
do not preserve or commit the preexisting pnpm-generated node_modules tree.

Handoff local content-safety and staged diff checks passed. The broad local
secret scan reported matches only inside untracked Playwright node_modules;
it is not recorded as a clean-workspace PASS. Repeat the unchanged scanner on
the separate clean remote clone before installing dependencies. No matched
dependency files are staged or uploaded.

| Local category | Disposition before formatting |
| --- | --- |
| Product and validation source/tests/docs | Preserve on their existing remote branches; verify fresh clone and final SHA equality |
| node_modules, Python caches, downloaded browsers | Reproducible; do not upload |
| Ignored browser JSON and old screenshots | Unreviewed raw artifacts; not uploaded; sanitized current findings preserved here |
| Old extracted source archive at baseline `9a3b9ea` and tarballs | Historical reference, not active worktree; not assumed identical without comparison; retain externally pending owner review |
| Old workspace named PerfectMatch Plane | Separate unborn Git repository: no commit, extensive untracked historical addons/docs/patches/staging/evidence. Not safe to assume synchronized with GitHub or OneDrive |
| Historical M25 source package / human IP review material | External proprietary source; never upload raw content. Secure backup/availability confirmation outside Git required if still needed |
| Temporary earlier-UAT password files and local access configuration | Do not upload; regenerate disposable identities. Restore GitHub/SSH access through approved credential management; do not reuse temporary credentials |

No local files are deleted by this mission. Historical patches/drafts and raw
artifacts have NOT been fully reconciled with remote history. They are outside
the focused source commit, not silently discarded. Before format, the owner
must verify an encrypted off-workstation backup of necessary historical work
and private material, or explicitly classify each as disposable/reproducible.
Cloud-sync placement alone is not proof of a recoverable backup. Project-wide
format readiness remains NO until this residual preservation is confirmed.
No private material contents are included here. Signing authority, backup age
identities, SSH private keys or retained instance configuration, if needed,
belong only in approved secure storage, never in GitHub. Do not copy databases
or filestores into this repository.

## Fresh Workstation Recovery

Use Linux Ubuntu 24.04 (the CI runner baseline) or an isolated equivalent Linux
VM for Docker runtime tests. Windows can edit/clone; Windows-native runtime
parity is not certified. Install Git, Bash, Docker Engine with Compose v2,
Python 3.12, Node.js 22 with npm, jq, curl, OpenSSL, GNU coreutils, tar and gzip.
Use repository scripts for additional age/systemd rehearsal prerequisites.
No exact Docker/Git minor version is locked; use the CI-compatible capabilities
and confirm `docker info` / `docker compose version`, not guessed pins.
Runtime images are digest-pinned in `deployment/runtime/runtime-lock.json`
(Odoo19, PostgreSQL15, Alpine3.20, Nginx1.27). Browser package-lock v3 pins
Playwright 1.63.0 and axe 4.13.0. Do not upgrade dependencies during recovery.

Authenticate GitHub using the official integration, SSH agent or credential
manager. Never put a token into clone URLs, commands, docs or logs.

```bash
git clone https://github.com/Cloud-Pixel-Studio/perfect-match-qms.git perfect-match-qms
cd perfect-match-qms
git fetch origin
git switch main
git rev-parse origin/main
git worktree add -b codex/m31-4-c4-scoped-configuration-action-access ../qms-product origin/codex/m31-4-c4-scoped-configuration-action-access
git worktree add -b codex/m31-4-c4-1-integration-browser-acceptance ../qms-validation origin/codex/m31-4-c4-1-integration-browser-acceptance
git -C ../qms-product rev-parse HEAD
git -C ../qms-validation rev-parse HEAD
git -C ../qms-validation status --short
```

Compare with the handoff SHA in #151/#146/#148, and the product SHA above. Do
not reset if branches have advanced. Read this document from qms-validation.
No old workstation path is required for any recovery command.

```bash
cd ../qms-validation
npm ci --prefix tools/tests/UAT
npx --prefix tools/tests/UAT playwright install --with-deps chromium
python deployment/scripts/validate-addons.py
python deployment/scripts/secret-scan.py
python deployment/scripts/qms-content-safety.py
python -m unittest tools.security.test_m27_evidence tools.security.test_pip_audit_evidence
git diff --check
```

Only on an authorized disposable Linux runner, never a shared customer host:

```bash
bash deployment/scripts/tests/test_customer_authenticated_uat.sh
bash deployment/scripts/odoo-dev.sh test-mission16
bash deployment/scripts/odoo-dev.sh test-mission23
PMQMS_SECURITY_RUN_ID=resume-m314c42 bash deployment/scripts/security-audit.sh
```

The UAT script creates and removes a local fictional tag for bundle testing;
never push that tag. It generates disposable database/password/license fixtures
and cleans up on EXIT. Do not transplant these into a real installation. The
test-failure diagnostics and direct probes need correction before acceptance.
For focused Odoo coverage, use the established runner and
`TestM314ConfigurationAccess` in `test_m31_4_configuration_access.py`; do not
substitute Python unittest outside Odoo for this ORM suite.

Preferred complete gate: existing PR QMS CI (`.github/workflows/qms-ci.yml`)
and Security Audit (`.github/workflows/security-audit.yml`). A new branch push
triggers PR workflows. Actions UI can rerun the selected existing run; Security
Audit also supports workflow_dispatch. Record run, branch head, base and actual
checkout SHA. Never rerun a stale SHA and label it current. Inspect step skips
and results, not only a badge. No new commit is needed just to rerun a check.

## Configuration and Secrets Outside Git

The disposable runner supplies these names; do not copy old values:
`PMQMS_CUSTOMER_INSTANCE_ROOT`, `M31_BASE_URL`, `M31_DATABASE`,
`M31_ORGANIZATION_NAME`, `M31_ACTION_MANIFEST_FILE`, `M31_HEADLESS`,
`M31_BROWSER_CHANNEL`, `M31_JSON_REPORT`, `M31_OUTPUT_DIR`, and pairs
`M31_<ROLE>_LOGIN` / `M31_<ROLE>_PASSWORD_FILE` for roles `QM`, `ADMIN`,
`QMS_ADMIN`, `LICENSE_ADMIN`, `AUDITOR`, `OWNER`, `VIEWER`, `API`.
`PMQMS_SECURITY_RUN_ID` labels security evidence. Password variables name
restricted files, not plaintext passwords. The runner uses OpenSSL to generate
fresh random passwords and an ephemeral Ed25519 signing key confined to its
temporary fixture. Never regenerate or replace the real license authority
under a UAT instruction. Restore real GitHub permissions, SSH/network access,
secret-manager access and any necessary signing/backup authority separately.

## Next Steps and Acceptance

1. Verify remote heads and clean clone; finish external historical/private
   backup disposition before formatting. Keep #151 draft, #147 unchanged.
2. Reproduce the product Framework Administration regression in a disposable
   Odoo test; identify whether permission semantics or the test is wrong.
3. Isolate Licensing Admin openRootMenu with bounded operations and sanitized
   DOM/response diagnostics. Confirm actual hover/click behavior; no hidden
   element force-display or synthetic click alone as user acceptance.
4. Separate direct-action tests from navigation failures and assert XML-ID,
   target model, correlated JSON-RPC success/error, real rendered screen,
   protected record/field access and mutation results independently per role.
5. Complete fictional data/workflow/company isolation coverage, all required
   widths, and target-model/action mutation checks without broad ACL grants.
6. Make only reproduced product corrections on #150; merge normally into #151.
   Resolve sudo review through documented evidence, never by suppression.
7. Require focused Odoo tests, full Mission23/QMS, authenticated browser matrix,
   Security/OpenGrep/Trivy, secret/content checks and unconditional cleanup on
   the exact candidate. Record failing/skipped cases truthfully. Product Owner
   review is still required; no merge is authorized by this document.

Read root `AGENTS.md`, `addons/AGENTS.md` before addon work,
`docs/GITHUB_GOVERNANCE.md`, `docs/DECISIONS/ADR-079-quality-manager-configuration-access-contract.md`,
`docs/NAVIGATION_ARCHITECTURE.md`, `docs/TECHNICAL_ADMINISTRATION_BOUNDARY.md`,
`tools/tests/UAT/README.md`, `deployment/runtime/README.md`,
`docs/BACKUP_AND_RECOVERY.md`, and the workflow/runner files cited above.
This WIP handoff takes precedence over stale PASS wording in prior PR comments
only as an evidence correction; it does not change the approved security contract.
