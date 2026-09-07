# M31.2 CleanVM Customer Installation and UAT Evidence

## Source Identity

- Main SHA: `bc4d6177219bd2d003de1b16d6a9b96b1582cb09`
- Post-merge QMS CI: `34067459977` SUCCESS
- Post-merge Security Audit: `34067459982` SUCCESS
- Environment: disposable test instance only

The evidence below uses the same exact main SHA throughout. No Demo,
production, `cleanvm-test-02`, or real customer environment was modified.

## Fresh Installation

- Instance: `m31-final-cert-test`
- Fresh instance: YES
- Bundle: `v99.99.91-rc0`
- Bundle source SHA: `bc4d6177219bd2d003de1b16d6a9b96b1582cb09`
- Bundle checksum: `2e67a617238801450596312f38f537a7e79796f82cd66d3040a2aa5dfa3c2f67`
- Provisioning: PASS
- Operator checkout leakage: NO

The local-only test tag was never pushed and was removed after certification.

## License and Customer Bootstrap

- Bootstrap without license: PASS
- Pre-license status: `missing`
- Activation request: PASS
- Signed test license import: PASS
- License status: VALID
- Environment match: YES
- Customer: M31 Final Certified Customer, Inc.
- Operational organization code: `M31CERTFINAL`
- First Quality Manager scope: configured, operational organization matched,
  all sites, all processes, system administrator: NO
- Site: visible and effective in scope
- Customer ready: YES
- Manual repair: NO

## Exact Merged Harness

The harness was run from the exact merged-main source with no local source
modifications.

- Harness: 6 passed, 1 permitted Viewer skip, 0 failures
- Quality Manager main flow: PASS
- Domain smoke: PASS
- Accessibility baseline: PASS
- Configuration: reachable directly
- Company Profile, Sites, Processes, Users & Access, Commercial License: PASS
- Guided implementation: PASS
- Counts: 37 controls / 20 operational processes / 37 control instances /
  118 activities / 111 generated tasks
- Sync 1 and Sync 2: zero growth (`0/0/0/0` each)
- Page errors: 0
- JavaScript errors: 0
- Unexpected 4xx: 0
- HTTP 500: 0
- RPC failures: 0
- No new accessibility regression

Known findings were reproduced only as previously documented: the generic
Implementation New/Create bypass (P1) and Management Review navigation not
exposed (P2). No new P0, P1, or P2 was found.

## Restart and Backup

After a controlled runtime restart, health, valid license, customer-ready
status, and counts remained unchanged.

- Backup instance: `m31-backup-cert-test`
- Backup: PASS
- Product version: `v99.99.91-rc0`
- Release SHA: `bc4d6177219bd2d003de1b16d6a9b96b1582cb09`
- Encryption: real `age` 1.2.1
- Official age archive SHA: `7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50`
- Backup archive SHA-256: `7e61ecfe473dded1ad83d7642ae4b1fcb32b7fe0e1c670bddc90788d987666f3`
- Backup checksum: PASS
- Manifest schema and release identity: PASS
- Required components: PASS
- Off-host archive, manifest, and checksum: present
- Decryption and internal verification: PASS
- Private identity in backup: NO
- Private signing key in backup: NO
- Password or credential markers in backup payload: NO

The earlier backup attempt stopped before product backup execution because the
host could not resolve `github.com` to obtain the pinned age tool. That was an
operator/host prerequisite issue, not a PMQMS product defect.

Both the initial product certification and this backup closure used the same
exact source SHA. All disposable instances, temporary credentials, age key
material, staged artifacts, and the local test tag were removed afterward.

## Scope

This evidence change adds documentation only. Product files changed: 0.
Test files changed: 0. No release tag or GitHub Release was created.
