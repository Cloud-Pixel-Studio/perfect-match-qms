# Perfect Match QMS v1.0.0-rc7

## Secure Offline Licensing And Commercial Entitlements Release Candidate

RC7 freezes the standalone Perfect Match Digital QMS baseline after Mission 20.
It packages signed offline licensing, environment binding, commercial capacity
enforcement, and the customer-facing license experience without adding an
online licensing service or billing system.

## Included

- Ed25519-signed offline license documents using schema version 1.
- External environment identity that survives normal container lifecycle and is
  not stored in the database or repository.
- Activation-request generation and controlled license import through Odoo.
- Atomic replacement of the current license and anti-rollback revision checks.
- Server-side limits for operational companies, active Sites, and active named
  QMS users.
- One named-user seat for a user with multiple QMS roles.
- Capacity release when a Site or named user is archived, with protected
  technical/support exemption handling.
- Commercial License status and entitlement usage in the QMS application.
- A valid fictional Demo license for the isolated `pmqms_demo` environment.
- The Mission 20 Commercial License read-only list regression fix, so normal
  users open the existing license instead of an accidental blank creation form.

## Security And Customer Safety

- License validation is cryptographic, environment-bound, and independent from
  Odoo role, Site scope, process scope, and workflow security.
- Payload and signature tampering, unknown keys, malformed documents, wrong
  environments, invalid replacements, and older revisions are rejected.
- License state never deletes, encrypts, corrupts, or hides customer records.
  Existing QMS data, attachments, exports, and backups remain available.
- Capacity enforcement applies to new or reactivated licensed capacity. RC7 does
  not introduce an unsafe global expired-license write lock.
- Private signing keys, Demo administrator passwords, customer data, database
  dumps, filestore archives, and local secret files remain outside GitHub.
- Proprietary Perfect Match wording remains separate from external standard
  names and clause identifiers.

## Validation

- Odoo Mission 20 suite: 136 tests, 0 failures, 0 errors.
- Standalone dependency audit: no mandatory Sales, Purchase, Inventory, MRP,
  HR, Accounting, Odoo Quality, or Maintenance application dependency.
- Repository checks cover addon manifests, XML, shell syntax, secret scanning,
  content safety, diff hygiene, and DEV/Demo configuration.
- Demo validation remains isolated to `pmqms_demo`; the canonical fictional
  Apex organization has three Sites and the current signed Demo license.
- Authenticated Demo validation covers Dashboard, Company Profile, Sites,
  Processes, Equipment, Users & Access, Commercial License, Action Center and
  source navigation, Cost Analytics, and major QMS menus.

## Deliberate Non-Claims

RC7 does not include:

- an online license server, phone-home, telemetry, or automatic revocation;
- subscription billing, Stripe, a customer purchasing portal, or a commercial
  account console;
- a full customer installer, deployment factory, or Mission 21 work;
- automatic expired-license restricted write mode;
- certification, external compliance approval, or customer production approval.

## Environments

- DEV remains the engineering, install, upgrade, and regression environment.
- Demo remains the only public fictional validation environment.
- The Oliva Torras pilot remains retired and is not part of this release.

The release baseline, exact final main SHA, tag verification, GitHub prerelease,
Plane work item, and final Demo evidence are recorded in
`docs/RELEASE_BASELINE_v1.0.0-rc7.md` and the RC7 release report.
