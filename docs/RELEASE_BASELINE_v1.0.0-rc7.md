# Perfect Match QMS v1.0.0-rc7 Release Baseline

## Release Identity

| Field | Value |
| --- | --- |
| Previous release | `v1.0.0-rc6` |
| RC6 tag commit | `4135f478d0d2be9000b3e05402b833fb0901da19` |
| Mission 20/main source before RC7 docs | `5f994531f5402b8ac7212ae12be5da6af1f7b610` |
| Final main commit | Recorded at final merge and verified against the RC7 tag target |
| RC7 tag | `v1.0.0-rc7`, annotated after all release gates pass |
| Addon version | `pm_qms_license` `19.0.1.0.0` |
| License schema | `1` |

The final main commit is the immutable commit targeted by `v1.0.0-rc7`; the
release report records the exact SHA after canonical main is merged. The tag's
peeled commit must equal that final main SHA.

## Licensing Baseline

- Addon: `pm_qms_license`.
- Algorithm: Ed25519 over canonical UTF-8 JSON with sorted keys, compact
  separators, and no ASCII escaping.
- Approved public key ID: `pmqms-demo-2026`.
- Approved public key fingerprint:
  `b9b6bff1d7b6738162bbfd6250c866f5cbb1a5e72e7a245ce0876d07818de31e`.
- Private signing material is external to the repository and is never part of
  the release artifact.
- Environment identity is generated and persisted in the deployment secret
  configuration, outside PostgreSQL and outside Git.
- Supported license states include valid, expiring, expired, not-yet-valid,
  invalid signature, wrong environment, and invalid format.
- There is no permanent Internet or phone-home requirement.

## Entitlement Baseline

- Company capacity counts active operational organizations only.
- Framework organizations do not consume operational company capacity.
- Site capacity counts active Sites attached to active operational organizations.
- Named-user capacity counts active internal users with QMS roles once, even if
  the user has multiple roles.
- Archiving a Site or named user releases capacity; reactivation is checked
  again server-side.
- Normal operational users cannot self-assign a licensing exemption.
- The current capacity check serializes on the current license row before usage
  is re-read.

## Active Lifecycle

| Environment | Role | Status |
| --- | --- | --- |
| DEV | Engineering, install, upgrade, and regression validation | Active |
| Demo | Fictional customer-facing validation | Active |
| Oliva Torras pilot | Historical customer-specific technical pilot | Retired |

The Demo is isolated in database `pmqms_demo`, with the fictional Apex
Precision Systems organization and the three canonical Sites `APEX-HQ`,
`APEX-MFG`, and `APEX-INS`. Its current license is `PMQMS-DEMO-2026`.

## Quality Evidence

- Current Odoo test total: 136.
- Required result: 0 failures and 0 errors.
- Standalone audit: no mandatory dependency on Sales, Purchase, Inventory, MRP,
  HR, Accounting, Odoo Quality, or Maintenance.
- Fresh-install and RC6-style upgrade checks are performed through the
  repository-supported DEV workflow; Demo seed is restricted to `pmqms_demo`.
- Secret scan, content-safety scan, addon/manifest validation, XML validation,
  shell syntax, diff check, compile, configuration, health, and backup checks
  are release gates.
- Mission 19 role, Site scope, process scope, workflow, segregation, Action
  Center, Dashboard, and Cost of Quality regression evidence is required before
  finalization.

## Customer Data And Migration Semantics

License state does not delete or make customer records inaccessible. Records,
attachments, exports, and backups remain preserved. Capacity enforcement blocks
new or reactivated licensed capacity when limits are exceeded. Expiry does not
implement a global write lock in RC7.

Environment identity is persistent across normal restart and supported
container recreation. A legitimate server migration requires a license reissue
when the new environment identity differs; the environment binding is not
weakened to avoid that requirement.

## Artifact Safety

The release contains source, tests, documentation, and release metadata only.
It excludes private keys, passwords, API tokens, database dumps, filestore
archives, customer attachments, activation secrets, and internal credentials.

RC7 does not start Mission 21.
