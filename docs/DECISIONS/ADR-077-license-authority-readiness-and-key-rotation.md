# ADR-077: License Authority Readiness and Key Rotation

## Status

Implemented for the separate Demo/QA bundle; not enabled in the standard
customer/production bundle.

## Context

The shipped runtime registered `pmqms-demo-2026` as its only verification
authority. Its corresponding private issuance key was no longer available to
the operator, so a new clean environment could not receive a valid signed
license even though signature enforcement was working correctly.

## Decision

Keep `pmqms-demo-2026` and `pmqms-license-2026` in the standard public verifier
registry for historical validation and active general issuance. The separate
Demo/QA bundle carries `deployment/demo/public_keys_demo_qa.json`, while the
customer bundler removes `deployment/demo` and `deployment/docker/demo`. The
v2 payload also requires the signed `deployment_scope=demo-qa` field. Both the
bundle-specific registry and signed scope are required; `key_id` alone is not
an environment authorization mechanism.

The original active authority remains at:

`/opt/perfect-match/secrets/license-authority/pmqms-license-2026.pem`

The file is owner-readable (`0600`) and the directory is restricted. Only
public keys are committed only to the appropriate bundle registry. The general
issuer default remains `pmqms-license-2026`; this PR does not issue a `.pmql`
or copy private material anywhere.

## Security and operational boundaries

- Private signing material is never committed, bundled, copied to a customer
  instance, or mounted into persistent customer storage.
- License verification continues to require a valid signature, approved key,
  and matching environment identity.
- The two standard shipped authorities coexist; no existing license is
  silently migrated or invalidated. Demo/QA additionally loads v2 only through
  its dedicated read-only bundle mount.
- Dockerized issuance must preserve `0600` and use a controlled invoking
  host UID/GID when container access is required.
- CI uses ephemeral generated test key pairs and does not depend on the real
  operator private key.

## Consequences

The v2 private key is preserved externally and is not distributable. Standard
customer/production verification rejects v2; the Demo/QA importer accepts it
only with the signed scope and dedicated bundle registry. Historical licenses
remain valid until retired through the normal lifecycle.
