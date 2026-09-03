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

Only public verification keys are shipped in `data/public_keys.json`.
`pmqms-demo-2026` remains registered as a historical verifier, while
`pmqms-license-2026` is the active issuance authority. The corresponding
private signing key lives outside Git, Docker images, and customer instances
at `/opt/perfect-match/secrets/license-authority/pmqms-license-2026.pem`,
owner-readable only. `key_id` and public-key fingerprints allow rotation while
old and new signed licenses remain verifiable without changing the license
format. Verification is entirely local: the product has no phone-home call,
license cloud dependency, or continuous Internet requirement.

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
