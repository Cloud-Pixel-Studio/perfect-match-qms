# ADR-059: Signed Offline Commercial Licensing

## Status

Accepted for Mission 20.

## Context

Perfect Match QMS needs commercial capacity controls without coupling QMS
permissions to billing, requiring continuous Internet access, or placing
customer data behind an unsafe expiry lock. The product is self-hosted and may
run in isolated networks.

## Decision

Use a standalone `pm_qms_license` addon. Bind a signed versioned `.pmql`
document to an external persistent environment UUID. Verify Ed25519 signatures
locally with the established `cryptography` library and a versioned public key
registry. Keep private signing keys outside Git, images, and customer
deployments.

Enforce only capacity in this mission: one operational company environment,
active Sites, and active named QMS users. Framework organizations are excluded;
additional operational companies use isolated environments. Use a row-level
transaction lock around capacity checks to serialize concurrent activations.

Expose status, usage, environment identity, activation request, import, and
history in Odoo. Import validates first and replaces the current license
atomically. License failure never deletes or encrypts data, prevents backup, or
removes read/export access. A global expired-license write restriction is
deferred until it can be designed safely across the model surface.

## Consequences

The deployment operator must preserve the identity file during migrations and
issue a new license when intentionally creating a new installation. Offline
customers can continue operating without a license service. Commercial
support must manage key rotation, revision issuance, and the external secret
store. Customers with root or source access can bypass self-hosted controls;
the goal is professional, tamper-evident entitlement enforcement rather than
unrealistic DRM.
