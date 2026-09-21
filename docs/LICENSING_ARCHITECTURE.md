# Commercial Licensing Architecture

Mission 20 adds commercial capacity licensing as a layer separate from Mission
19 identity, permissions, and site/process scope. Odoo remains the system of
record for QMS data and business rules. Licensing does not replace Odoo ACLs or
record rules.

## Environment identity

Each installation has one UUID in the deployment secret/configuration area,
outside the normal database. The active Compose stacks mount it read-only at
`/etc/odoo/environment_id`; `PMQMS_ENVIRONMENT_ID_FILE` can override the path.
The file is created once in the deployment-managed secret/configuration area
and is not derived from a container ID, hostname, IP, MAC, disk, or CPU. It is
not a credential; the runtime receives read-only access to the identifier.
Container recreation and normal upgrades therefore preserve the identity.

For a server migration, copy the identity file through the approved secret
backup process before starting the new stack. If the installation is intended
to become a new licensed environment, generate a new identity instead and
issue a new license. A database clone must never be paired with the old
identity accidentally.

## Signed offline license

The `.pmql` document is JSON containing a versioned payload and a detached
base64 signature. Ed25519 verification uses the `cryptography` library. The
payload is canonicalized as UTF-8 JSON with sorted keys, compact separators
`(',', ':')`, and `ensure_ascii=False`; only that byte sequence is signed.
Required payload fields include `schema_version`, `license_id`,
`license_revision`, customer/edition, environment UUID, company/site/named-user
limits, dates, perpetual flag, and `key_id`.

The standard customer/production verifier ships only the public keys in
`data/public_keys.json`: `pmqms-demo-2026` remains a historical verifier and
`pmqms-license-2026` remains the active general issuance authority. The
separate Demo/QA bundle carries `deployment/demo/public_keys_demo_qa.json` via
a fixed read-only mount and removes that path from customer bundles. v2 also
requires the signed `deployment_scope=demo-qa` field. Therefore the Demo/QA
bundle boundary and signed scope are both checked; `key_id` or a mutable local
environment field alone is insufficient. Private signing keys remain outside
Git, Docker images, CI, and target instances.
Verification is entirely
local: the product has no phone-home call, license cloud dependency, or
continuous Internet requirement.

Supported states are missing, valid, expiring, expired, not-yet-valid,
invalid-signature, wrong-environment, and invalid-format. Perpetual licenses
use `expires_at = null`; term licenses use an explicit UTC timestamp.

## Capacity boundary

The standard entitlement is one operational company environment, three active
Sites, and one active named QMS user. `pm.qms.organization` is authoritative.
Organizations marked `framework` do not consume the commercial company count.
Additional customer companies are isolated environments, not ordinary second
operational organizations in one database.

Active Sites under the operational organization consume site capacity. Archived
Sites release capacity while retaining historical references. Active internal,
non-share users with at least one customer-facing QMS role consume one seat;
multiple roles still count once. Archived users, share users, technical/support
accounts, and privileged explicit exemptions do not consume a seat.

Capacity checks run server-side on organization/site/user activation and role or
account changes. A current license row is locked with `SELECT ... FOR UPDATE`
while usage is re-read, serializing competing capacity activations without a
global write lock. The service never modifies a project-management database
directly.

## Data safety

License failure never deletes, encrypts, corrupts, or hides customer data. The
database remains backupable and records/attachments remain readable and
exportable. Mission 20 enforces capacity for new activation; it deliberately
does not add an unsafe global expired-license write lock or a BaseModel
monkey-patch. A future restricted operational mode needs a separate design.

## External authority boundary (preparatory)

The signing authority is external to PMQMS runtime environments. The target
Demo/QA design is:

```text
AWS administrator -> KMS CMK -> Secrets Manager (Ed25519 PEM)
       |                         |
       +-> S3 Object Lock backup +-> controlled issuer role
       +-> CloudTrail audit      +-> recovery role (dual approval)
```

The issuer may read the exact authority secret only for an approved issuance
operation. Customer VMs receive only the resulting `.pmql`; they never receive
the private key or AWS credentials. The recovery role is separate from the
issuer role and is not available to customer operators.

The design requires a dedicated secret, CMK, private versioned S3 bucket with
Object Lock, CloudTrail, MFA, and two-person approval. Exact IAM permissions
and the administrator checklist are documented in
`docs/security/PMQMS_AWS_IAM_LICENSE_AUTHORITY.md` and
`docs/PMQMS_AWS_AUTHORITY_APPROVAL_CHECKLIST.md`.

`pmqms-demo-2026-v3` remains proposed only. Its key, fingerprint, public-key
registration, and license issuance are blocked until the external store is
approved and recovery has been tested.
