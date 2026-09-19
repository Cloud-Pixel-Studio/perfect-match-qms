# ADR-077: License Authority Readiness and Key Rotation

## Status

Accepted for implementation on the M30.3 corrective branch.

## Context

The shipped runtime registered `pmqms-demo-2026` as its only verification
authority. Its corresponding private issuance key was no longer available to
the operator, so a new clean environment could not receive a valid signed
license even though signature enforcement was working correctly.

## Decision

Keep `pmqms-demo-2026` and `pmqms-license-2026` in the public verifier registry
for historical validation and active general issuance. Add
`pmqms-demo-2026-v2` as the explicitly scoped Demo/QA issuance authority. Its
new Ed25519 private key is generated and retained only in the external
operator-controlled secret store at a path outside the repository and Demo VM.

The original active authority remains at:

`/opt/perfect-match/secrets/license-authority/pmqms-license-2026.pem`

The file is owner-readable (`0600`) and the directory is restricted. Only
public keys are committed to the addon registry. `issue-license.py` selects the
Demo/QA authority explicitly with `--key-id pmqms-demo-2026-v2`; the general
issuer default remains `pmqms-license-2026`.

## Security and operational boundaries

- Private signing material is never committed, bundled, copied to a customer
  instance, or mounted into persistent customer storage.
- License verification continues to require a valid signature, approved key,
  and matching environment identity.
- All three public keys coexist; no existing license is silently migrated or
  invalidated.
- Dockerized issuance must preserve `0600` and use a controlled invoking
  host UID/GID when container access is required.
- CI uses ephemeral generated test key pairs and does not depend on the real
  operator private key.

## Consequences

Clean disposable and customer-style environments can be licensed using the
active external authority without weakening verification. Operator key
rotation is explicit and auditable through `key_id` and public-key
fingerprints. The old Demo-era verifier remains trusted until its issued
licenses are retired through the normal license lifecycle.
