# Perfect Match QMS v1.0.0-rc9

## Release Freeze

RC9 is the release candidate freeze for the standalone Perfect Match Digital
QMS after Mission 23. It contains the generic QMS platform, the separated
`pm_qms_iso9001` standard add-on, the commercial license foundation, the
customer deployment tooling, and the hardened Product Shell.

RC9 does not add another standard, a billing service, an ERP connector, an AI
orchestration layer, or a new customer workflow. It is a release validation
and packaging gate, not a certification claim.

## Included Baseline

- Generic QMS core remains usable without `pm_qms_iso9001` installed.
- ISO 9001 is the only implemented standard add-on and depends downward on
  generic QMS modules.
- Framework Administration remains restricted to the authorized technical
  administrator role.
- Customer-facing shell, Product Shell navigation, Perfect Match branding,
  Action Center, Cost of Quality, Sites, Processes, and major QMS areas remain
  available through the supported application experience.
- Offline commercial licensing remains environment-bound and capacity-aware.
- Customer deployment tooling supports bundle, install, update, readiness,
  backup, and restore validation without including Demo or customer data.

## Validation Gate

The final RC9 report records the exact merged main SHA, immutable tag target,
customer bundle checksum, Demo deployed SHA, CI result, and authenticated
persona results. The release is not complete until every required gate is
green and the `v1.0.0-rc9` tag is verified against that final main SHA.

The required regression suite is 150 tests with zero failures and zero errors.
Release validation also covers fresh generic and ISO installs, idempotent
updates, customer deployment, license/readiness checks, backup/restore, Demo
validation, four customer personas, responsive shell behavior, and browser
console/traceback checks.

## Security And Intellectual Property

- Passwords, API keys, private signing keys, database dumps, filestore
  archives, customer files, Demo data, and activation secrets are excluded
  from GitHub, Plane, and customer bundles.
- Perfect Match wording remains proprietary. External mappings contain only
  standard names, editions, clause/reference identifiers, and internal notes.
- RC9 makes no claim of certification, external conformity, or customer
  production approval.

## Environments

- DEV is the engineering and regression environment.
- Demo is the fictional public validation environment.
- Customer validation uses disposable fictional test instances only.
- Historical customer-specific pilot environments remain retired and are not
  part of RC9 deployment.
