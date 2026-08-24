# Perfect Match QMS v1.0.0-rc9 Release Baseline

## Release Identity

| Field | Value |
| --- | --- |
| Previous release | `v1.0.0-rc8` |
| Final main commit | Recorded in the final RC9 report and verified against the tag |
| RC9 tag | `v1.0.0-rc9`, created only after all release gates pass |
| Product scope | Generic QMS plus `pm_qms_iso9001` |
| Implemented standards | ISO 9001 only |
| Required regression result | 150 tests, 0 failures, 0 errors |

The tag must be immutable and its peeled commit must equal the final canonical
`main` SHA. The final report records the exact SHA and all artifact checksums.

## Architecture And Standard Separation

- Generic QMS modules do not depend on `pm_qms_iso9001`.
- `pm_qms_iso9001` depends on generic QMS modules through the Quality Pack and
  does not duplicate generic controls, mappings, activities, or evidence.
- No other standard is implemented or exposed by the customer shell.
- Framework master-data administration is restricted; customer personas use
  the ISO 9001 experience without unsafe master-data access.

## Commercial And Deployment Baseline

- Offline signed license validation is environment-bound and remains separate
  from QMS role, Site scope, process scope, and workflow security.
- Customer bundles contain source, deployment tooling, manifests, tests, and
  documentation only. They contain no secrets, private keys, database dumps,
  filestore archives, Demo data, or customer data.
- Disposable customer validation covers install, license import, customer
  bootstrap, Sites, readiness, backup, and restore validation.

## Required Evidence

The final RC9 report must include PASS/PARTIAL/FAIL results for:

- CI and full DEV regression.
- Fresh generic/base and ISO installations, updates, and RC8 upgrade path.
- Customer bundle safety and checksum.
- Demo deployment, HTTPS, license, idempotent seed/update, and validation.
- Quality Manager, restricted QMS user, QMS Viewer, and Technical Administrator.
- Product Shell, branding, 1024px responsiveness, console, traceback, and
  direct URL security checks.
- GitHub prerelease, post-release smoke, and Plane release-item closure.

## Deliberate Non-Claims

RC9 is not an ISO certification, customer production approval, billing release,
ERP replacement, or implementation of any standard beyond ISO 9001.
