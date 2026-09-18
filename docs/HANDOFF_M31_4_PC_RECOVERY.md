# M31.4-C4.2 PC Recovery Handoff

Status: WIP / PRODUCT ACCEPTANCE BLOCKED. Snapshot: 2026-09-16.
This document preserves work, not a passing certification. The M31.4-C4.3
execution is still PARTIAL because authenticated browser UAT and downstream
CI evidence remain pending. The normal product-to-validation merge exists in
the validation history; no remote merge or release is claimed.
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

## M31.4-C4.3 Resume Evidence

The fresh-clone authority check was completed before editing: main resolved to
`d57ce391cc262c68d5bbe255eb53f448cd7356ff`, product resolved to
`0d66fd21e5ea1fcdba8e984febed626b835d0442`, and validation resolved to
`e8b866ad3f6ed934ee1916a1c14dacf2bc2b5315`. The required root/addon/governance,
recovery, navigation, boundary, UAT and runtime documents were read from that
clone. No advanced remote refs were detected.

Product commits `7784bf5`, `d7ed018` and `5a8cd18` correct the reproduced
Framework Administration regression by keeping migration below Configuration
and granting only the two migration wizard models to `base.group_system`.
The focused Mission16 run completed `0 failed, 0 error(s) of 266 tests`.
No broad legacy-manager or technical ACL was added.

Validation commits `3e95522` and `99e9b5a` bound the menu hover diagnostics
and split Configuration navigation from the direct action authorization
matrix into independent Playwright tests and browser contexts. The navigation
diagnostic records bounded actionability, viewport, geometry, computed display
state, `aria-expanded`, overlay candidates and the top element at the target
center. The direct matrix remains independently executed and records action
metadata, rendered screen cleanliness, authorization error correlation and
explicit NOT-PROBED states for protected data/mutation until those probes run.

Local normal merge commit `4f55f35` merges product into validation. It is
published through normal pushes: product PR #150 is at
`5a8cd18ff8b2203a587398da6a100ff8a637e898`. Validation PR #151 was published
at `71941ddb2d343285e6716342b9c6cb534f03f7ae` and this handoff update was
published as `f50f8d319e448fa4d9c486ac2defa14f2197f5ac`; the follow-up
documentation revision is `fe38f05cede5705dac1922bf4e7a4a7320d561b5`. PR #151
remains draft. PR #147 remains open and unchanged. No force push was used.

The disposable authenticated UAT reached provisioning, 61-module bootstrap
and customer HTTP health 200, then failed before browser setup because the
Windows Docker Desktop/WSL bind mount did not expose
`activation-request.json` to the post-command host-side check. Cleanup passed,
but this is not a UAT PASS and does not certify Linux runtime parity. The
remaining browser acceptance, viewport matrix, direct protected-data/mutation
probes, full Mission23/QMS, Security/OpenGrep/Trivy and exact remote-head CI
are pending.

### Current checkpoint

```text
STATUS: PARTIAL
MAIN_SHA: d57ce391cc262c68d5bbe255eb53f448cd7356ff
PRODUCT_LOCAL_SHA: 5a8cd18ff8b2203a587398da6a100ff8a637e898
VALIDATION_LOCAL_SHA: 4f55f35
PRODUCT_REMOTE_SHA: 0d66fd21e5ea1fcdba8e984febed626b835d0442
VALIDATION_REMOTE_SHA: e8b866ad3f6ed934ee1916a1c14dacf2bc2b5315
PRODUCT_REMOTE_SHA: 5a8cd18ff8b2203a587398da6a100ff8a637e898
VALIDATION_REMOTE_SHA: 71941ddb2d343285e6716342b9c6cb534f03f7ae
REMOTE_PUSH: PASS_NORMAL_PUSH
REMOTE_MERGE: NOT_PERFORMED
RELEASE_OR_PRODUCTION_CHANGE: NO
UAT: BLOCKED_BEFORE_BROWSER_BY_WINDOWS_DOCKER_BIND_MOUNT
MISSION16: PASS_266_0_0
CLEANUP: PASS
```

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

## M31.4-C4.5 Licensing Navigation and Runtime Authorization Checkpoint

Candidate evidence was published without force-push.  The authoritative SHAs
at the last completed gate were:

- `origin/main`: `d57ce391cc262c68d5bbe255eb53f448cd7356ff`
- PR #150 product: `d0678c119167a6a7fd8db3f1317994c52797458f`
- PR #151 validation: `01d0043e233339fed58b41b54a517679ac1f6dc6` (PR #151
  remains draft)
- product-to-validation normal merge: `51ec492799cf2a8d85f00c35879a23f2ca755aeb`

The product correction is limited to removing the shared app-root action so a
license-only role does not trigger an unauthorized dashboard read; Dashboard
remains an explicit child action.  The Licensing Administrator normal
Configuration route now passes at 1600x900, 1280x720 and 1024x720.  The first
diagnostic divergence was in the validation harness: the direct Commercial
License probe observed no action-load response before its bounded wait, and
the QMS Framework Administration menu is a parent group whose navigable child
is Framework Controls.  The harness now uses fresh contexts per direct probe,
has a bounded action-metadata fallback, and validates the child action.

The completed candidate QMS run was `35244397828` on the exact SHA above:
all 63 job steps completed successfully; browser UAT passed,
direct authorization was 23/23, protected reads and field denial passed,
permitted create/write passed, prohibited create/write/unlink probes passed,
company isolation returned zero out-of-company records, and cleanup passed.
Mission16 and Mission23 both ran and completed; no downstream stage was
skipped.  Workflow transitions remain `NOT TESTED` because this release
exposes no supported transition method and no synthetic state write was used.

Security Audit run `35244397710` passed on the same candidate.  The local
control record remains: OpenGrep v1.29.0 local rules and positive/negative
tests pass; Trivy 0.74.0 vulnerability/misconfiguration/secret scans pass;
secret and content scans pass; sudo inventory/review and XML/Python/addon/
workflow validation pass; `git diff --check` passes.  Canonical pip-audit is
`NOT_EXECUTED` because no dependency input is declared; Issue #98 remains the
tracked follow-up.  No credentials, private keys, databases, filestores,
raw browser traces or node_modules were uploaded.

No PR was merged, no release or tag was created, PR #151 remains draft, and
PR #147 is unchanged.  Product Owner review is the next approval gate.

## M31.4-C4.7 Controlled Product Merge and Post-Merge Validation

Product PR #150 was merged only after rechecking its exact HEAD
`d0678c119167a6a7fd8db3f1317994c52797458f`.  The normal merge commit is
`5aa735c7b09dfa46cfab8ca5d9d725039d4b982e`, now the exact `origin/main`.
No squash, rebase, force push, release, tag, or history rewrite was used.

Post-merge QMS CI `35260595200` passed on that merge SHA.  All 33 functional
steps and post-job cleanup passed, including Mission16 and Mission23; no
workflow step was skipped.  The main-branch QMS workflow does not include the
authenticated browser UAT.  A manual post-merge harness attempt confirmed
cleanup but emitted no UAT success marker, so post-merge authenticated UAT is
`NOT TESTED` and must not be inferred from QMS.  The post-merge workflow
authorization transition also remains `NOT TESTED` because the release
exposes no supported workflow transition method and no synthetic state write
was accepted as evidence.

Post-merge Security Audit `35260595185` passed on the same SHA.  OpenGrep
local/pinned rules, Trivy vulnerability/misconfiguration/secret scanners,
secret scan, content safety, sudo review, XML/Python/addon/workflow checks and
git diff check passed.  pip-audit remains `NOT EXECUTED` under Issue #98 due
to the missing canonical dependency input.

PR #151 remains open and draft as validation-only; PR #147 is unchanged;
Issues #146 and #148 remain open.  Demo, production, customers, CleanVM,
repository protections, releases and tags were not modified.

## M31.4-C4.8 Post-Merge Authenticated UAT Against Main

Live verification before synchronization confirmed `origin/main` at
`5aa735c7b09dfa46cfab8ca5d9d725039d4b982e` and PR #151 open/draft at
`056f2cc5be799313516a7b5e266f12734fd4d5ae`. PR #151 was synchronized with
main using the normal merge commit
`6dee1a7f8822a33ad0c32a63fb6216704eb6444f`; no rebase, force push or history
rewrite was used. The resulting remote PR head is that merge SHA.

QMS CI `35263307398` and Security Audit `35263307137` both completed
successfully on the exact validation head. QMS checkout and all 63 listed
steps completed; no step was skipped, including the disposable authenticated
UAT, Mission16, Mission23 and post-job cleanup. The authenticated UAT passed
its implemented assertions for the customer shell and the Quality Manager,
QMS Administrator, Licensing Administrator, Technical Administrator, Internal
Auditor, Process Owner, Viewer and API Integration Administrator fixtures.
The implemented direct authorization matrix remained 23/23 PASS. Protected
record reads, protected-field denial, permitted activation-request
create/write, prohibited organization create/write/unlink, prohibited
activation-request unlink, and same-company isolation all passed; disposable
mutation cleanup passed.

The evidence remains bounded by the actual test contract. The current browser
suite explicitly leaves customer branding, breadcrumbs, notifications,
keyboard navigation, visible focus, logout, and workflow transitions
`NOT TESTED`. The responsive More-menu path is also `NOT TESTED`; the
accessibility test covers axe checks and horizontal-overflow checks only at
1440x900 and 1366x768, not 1600x900, 1280x720 or 1024x720. Workflow
authorization is `NOT TESTED` because this release exposes no supported
transition method and no synthetic state write was used. These gaps are not
converted to PASS by the successful workflow. Direct customer restriction
URLs, Apps/Settings separation and database-manager blocking were exercised by
the implemented role-session tests and passed.

Security Audit `35263307137` passed. The repository control record remains:
OpenGrep v1.29.0 with local pinned rules and positive/negative tests PASS;
Trivy v0.74.0 vulnerability, misconfiguration and secret scans PASS;
secret-scan.py, qms-content-safety.py, sudo inventory/review,
XML/Python/addon/workflow validation and `git diff --check` PASS. pip-audit
is `NOT EXECUTED` under Issue #98 because the canonical dependency input is
still absent. No credentials, private keys, databases, filestores, cookies,
raw browser traces or node_modules were uploaded; cleanup was unconditional
and PASS.

PR #151 remains open and draft and was not merged. PR #147 remains unchanged;
Issues #146 and #148 remain open. Demo, production, customers, CleanVM,
repository protections, releases and tags were not modified. M31.4-C4.8 is
`PARTIAL`: the merged-main validation gate passed for implemented coverage,
but final closure requires explicit follow-up for the listed NOT TESTED
categories, especially 1600/1280/1024 responsive navigation and any supported
workflow transition.

## M31.4-C4.9 Complete Post-Merge UAT Coverage

Live verification remains consistent with the authorized revisions:
`origin/main` is `5aa735c7b09dfa46cfab8ca5d9d725039d4b982e` and PR #151 is
OPEN/DRAFT at validation head
`3218cbe44f8aa5833ea15962bfb3d2a6113bed5e`. The final exact-head workflows
are QMS CI `35265467009` and Security Audit `35265466947`; both PASS with no
skipped or failed steps. QMS ran the disposable authenticated UAT, Mission16,
Mission23 and cleanup.

Final coverage matrix:

| Category | Result | Evidence boundary |
| --- | --- | --- |
| Eight authenticated role sessions and customer shell | TESTED/PASS | QM, QMS Administrator, Licensing Administrator, Technical Administrator, Internal Auditor, Process Owner, Viewer and API Integration Administrator fixtures |
| Direct authorization | TESTED/PASS | 23/23 independent probes |
| Protected records/fields | TESTED/PASS | organization/license reads and protected-field denial |
| Permitted/prohibited mutations | TESTED/PASS | activation-request create/write allowed; organization and unlink denials enforced; cleanup passed |
| Company isolation | TESTED/PASS | no out-of-company records returned |
| Configuration and direct URLs | TESTED/PASS | implemented action/menu and restricted database-manager probes |
| Keyboard traversal | NOT TESTED | no complete traversal assertion in the current suite |
| Visible focus | NOT TESTED | axe does not certify focus styling |
| Responsive 1600/1280/1024 and More menu | NOT TESTED | current checks are only 1440x900 and 1366x768; More-menu coverage is explicitly untested |
| In-app notifications and record links | NOT TESTED | only bounded messaging-menu presence inspection exists |
| Reminders and activities | NOT TESTED | no independent notification/reminder recipient assertion |
| Chatter | NOT TESTED | no independent post/read assertion |
| SMTP disposable delivery | NOT TESTED | no supported disposable SMTP target is configured |
| Recipient isolation/duplicate notifications | NOT TESTED | no independent mail-delivery evidence |
| Workflow authorization | NOT TESTED | no supported real transition method exists; no synthetic write used |

Security controls on the exact validation head passed through Security Audit:
OpenGrep v1.29.0 local rules, Trivy v0.74.0 vulnerability/misconfiguration/
secret scanners, secret scan, content safety, sudo review, XML/Python/addon/
workflow validation and `git diff --check`. pip-audit remains `NOT_EXECUTED`
under Issue #98 because no canonical dependency input exists. Cleanup passed;
no credentials, cookies, private keys, databases, filestores, raw traces or
node_modules were uploaded. Cancellation-specific cleanup was not separately
exercised because GitHub Actions provides no safe post-cancellation assertion
for this disposable environment; this is `NOT TESTED`.

No product change was made. PR #151 remains OPEN/DRAFT and unmerged, PR #147
is unchanged, Issues #146 and #148 remain open, and no release/tag or
Demo/production/customer/CleanVM/protection change occurred. Status is
`PARTIAL`; M31.4 should not be closed until the remaining browser coverage is
implemented and executed on a supported disposable target.

## M31.4-C4.10 Complete Remaining UAT Coverage

The requested live pre-edit verification passed: main remained
`5aa735c7b09dfa46cfab8ca5d9d725039d4b982e`, and PR #151 remained OPEN/DRAFT at
`5d046179dc16e0ccdb91c1a1e02e37793bbe62aa`. QMS CI `35268195672` completed
PASS on that exact checkout. Every listed step completed successfully with
zero skips, including authenticated UAT, Mission16, Mission23 and cleanup.
Security Audit `35268195849` also completed PASS on the exact checkout with
zero skipped controls.

This run did not add coverage code or product behavior. The existing harness
therefore retains the following truthful classifications: role sessions,
23/23 direct authorization, Configuration, protected data, permitted and
prohibited mutations, company isolation, restricted URLs, UAT, Mission16,
Mission23 and normal cleanup are `TESTED/PASS`. Keyboard traversal, focus
order/visible focus, 1600x900/1280x720/1024x720, responsive More-menu
behavior, notification/reminder/activity delivery, chatter and record links,
overdue/expired notifications, duplicate and recipient isolation, and SMTP
capture are `NOT TESTED`. Workflow authorization is `NOT APPLICABLE/NOT
TESTED`: no supported real transition exists and no synthetic write was used.
Cancellation-specific cleanup is `NOT TESTED`; no safe GitHub Actions
post-cancellation assertion is available.

Security controls on this checkout were PASS through Security Audit: pinned
OpenGrep v1.29.0 local rules and positive/negative tests, Trivy v0.74.0
vulnerability/misconfiguration/secret scanners, secret scan, content safety,
sudo review, XML/Python/addon/workflow validation and `git diff --check`.
pip-audit remains `NOT EXECUTED` under Issue #98 because the canonical input
is absent. No product code, credentials, private keys, databases, filestores,
cookies, raw traces or node_modules were changed or uploaded.

The handoff update is documentation-only. PR #151 remains OPEN/DRAFT and is
not merged; PR #147 is unchanged; Issues #146 and #148 remain open. M31.4
remains `PARTIAL/BLOCKED FOR CLOSURE` until a supported disposable UAT adds
and executes the remaining browser and mail coverage.

## M31.4-C4.22 ORM Teardown File Access

The notification teardown harness was corrected on validation head
`63adf02853af3ca11c813f589b64732fd82000e1`. The previous failure was a
fixture-manifest `PermissionError` before ORM execution: the Odoo teardown
container ran as UID/GID `100:101`, while the runner-owned manifest was not
readable. The harness now prepares only the numeric-ID manifest with owner
`100:101` and mode `600`, mounts that single file read-only, records the
sanitized teardown UID/GID and permissions, and removes the manifest after
teardown. Passwords and other restricted files are not mounted into this
teardown container.

QMS CI `35356909115` completed PASS on the exact head in 16m35s. The focused
authenticated UAT, Mission16, Mission23, all downstream steps and normal
cleanup completed; no steps were skipped. The script returns nonzero unless
the ORM shell reads the exact fixture IDs, unlinks the risk and both
activities with `sudo()`, commits, and independently verifies no records
remain. Therefore this run confirms `riskRemoved=true`,
`qmActivityRemoved=true`, `viewerActivityRemoved=true` and `remaining={}`.
The final manifest is removed by harness cleanup.

Security Audit `35356909164` completed PASS on the same exact head. Its
repository controls passed, including local/pinned OpenGrep, Trivy,
secret/content scans, sudo review, XML/Python/addon/workflow validation and
`git diff --check`. No credentials, private keys, databases, filestores,
cookies, raw browser traces or node_modules were uploaded. pip-audit remains
`NOT EXECUTED` under Issue #98. SMTP/email, duplicate-notification coverage
and workflow authorization remain `NOT TESTED`/`NOT APPLICABLE` where no
supported target or real transition exists.

No product behavior or permissions changed. PR #151 remains OPEN/DRAFT at
this validation head and unmerged; PR #147 is unchanged; Issues #146 and
#148 remain open; no release/tag or Demo/production/customer/CleanVM/protection
change occurred. M31.4 remains `PARTIAL` for the separately untested browser
notification categories, but the C4.21 teardown blocker is resolved.
