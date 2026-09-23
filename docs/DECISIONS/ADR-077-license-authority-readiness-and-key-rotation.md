# ADR-077: License Authority Readiness and Key Rotation

## Status

Implemented for the separate Demo/QA bundle, including the registered v3
public key. This change does not issue a `.pmql` or authorize production use.

## Context

The v2 Demo/QA private issuance key became unavailable. A replacement v3
authority was created in the external controlled authority boundary, and its
local and S3-restored backups were verified before registering only its public
key in the Demo/QA bundle.

## Decision

Keep `pmqms-demo-2026` and `pmqms-license-2026` in the standard public verifier
registry for historical validation and active general issuance. The separate
Demo/QA bundle carries `deployment/demo/public_keys_demo_qa.json`, while the
customer bundler removes `deployment/demo` and `deployment/docker/demo`. The
v2 and v3 payloads require the signed `deployment_scope=demo-qa` field. Both
the bundle-specific registry and signed scope are required; `key_id` alone is
not an environment authorization mechanism. The Demo/QA bundle now contains
v3; the standard bundle remains unchanged and rejects both Demo/QA-only keys.

The original active authority remains in its approved external secret store.
Only public keys are committed to the appropriate bundle registry. The general
issuer default remains `pmqms-license-2026`; this PR does not issue a `.pmql`
or copy private material anywhere.

For v3, the canonical PMQMS fingerprint is SHA-256 over the raw 32-byte
Ed25519 public key:
`2b9b1f747ffa21e0aed00e461f661ca81536689a842566263ac96948e65d6ee7`.
SHA-256 over the same public key in SPKI DER encoding is
`34263f9060419a073fcd32f1cc956d6535092dfd1f16cbea2b28a9cc4c0db083`.
These are two encodings of the same key. Runtime validation and authority
records use the canonical raw-key fingerprint.

## Security and operational boundaries

- Private signing material is never committed, bundled, copied to a customer
  instance, or mounted into persistent customer storage.
- License verification continues to require a valid signature, approved key,
  and matching environment identity.
- `pmqms-demo-2026` and `pmqms-license-2026` remain unchanged in the standard
  bundle. The Demo/QA bundle preserves both historical keys and v2 while
  adding v3 through its dedicated read-only mount; no existing license is
  silently migrated or invalidated.
- Dockerized issuance must preserve `0600` and use a controlled invoking
  host UID/GID when container access is required.
- CI uses ephemeral generated test key pairs and does not depend on the real
  operator private key.

## Consequences

The v2 private key is considered irrecoverable. The v3 public key is registered
only in the Demo/QA bundle; standard customer/production verification continues
to reject Demo/QA-only authorities. Historical licenses remain valid until
retired through the normal lifecycle. No `.pmql` is issued by this change.

## Preparatory external authority

The v3 authority is kept outside the repository on the controlled authority
host. Its recovery archive is age-encrypted and has verified local and S3
copies. The age identity backup is KMS-encrypted and stored in the private S3
custody bucket using the PMQMS backup CMK. S3 Object Lock is not enabled for
this Demo/QA bucket. The Product Owner has approved a Demo/QA-only compensating
control set: S3 versioning, public-access blocking, SSE-KMS, age encryption
before upload, an issuer identity without object-delete permission, a separate
recovery identity, CloudTrail auditing, registered backup object/version
metadata, periodic restore tests, dual approval for recovery, and quarterly
integrity review. This exception applies only to Demo/QA. Object Lock remains
mandatory for production, and no production customer license may be issued
until a bucket with Object Lock is available. The private key and age identity
are never committed, bundled, or copied to customer instances, Docker, or CI.

This change registers only the verified v3 public key in the Demo/QA bundle
and documents custody and fingerprint formats. It does not change the standard
bundle or issue a `.pmql`.
