# PMQMS AWS Authority Approval Checklist

This checklist records administrator-owned infrastructure controls and
production gates. It does not authorize new key generation. The current v3
Demo/QA exception status is recorded below.

## Infrastructure

- [ ] Dedicated KMS CMK created and deletion protection configured.
- [ ] Secrets Manager secret created with the exact authority scope.
- [ ] Private S3 backup bucket created in the approved account and region.
- [ ] S3 versioning enabled.
- [ ] Production: S3 Object Lock and retention policy enabled before issuing
      any production customer license.
- [x] Demo/QA-only exception approved by the Product Owner. Object Lock is
      not enabled for the Demo/QA bucket; the compensating controls are
      documented in ADR-077 and `docs/PMQMS_LICENSE_BACKUP_RECOVERY.md`.
- [ ] Public access blocked.
- [ ] CloudTrail management events enabled for Secrets Manager/KMS and data
      events enabled for S3 backup objects under the exact recovery prefix.

## Access

- [ ] Issuer role created with the least-privilege policy.
- [ ] Recovery role separated from issuer role.
- [ ] Audit role cannot read or decrypt the private key.
- [ ] MFA required for recovery.
- [ ] Two-person approval recorded for recovery and rotation.
- [ ] No CI, GitHub, Docker, or customer VM access granted.

## Key lifecycle

- [ ] v3 key generated only in the approved external boundary.
- [ ] Public fingerprint independently verified.
- [ ] Encrypted backup created.
- [ ] Backup restored in a controlled test.
- [ ] Restored fingerprint matches the original.
- [ ] Temporary recovery artifacts destroyed.

## Repository gate

- [ ] Only the public key is proposed in a new branch and PR.
- [ ] Historical public keys remain present.
- [ ] Tests cover coexistence, invalid signatures, UUID, scope, key ID, and
      limits.
- [ ] QMS, Security Audit, OpenGrep, Trivy, secret scan, and content safety
      pass.
- [ ] Product Owner approves the PR.
- [ ] No `.pmql` is emitted before the PR is merged.

## Current status

`pmqms-demo-2026-v3` is generated and backed up for Demo/QA. Its public key is
proposed only in the Demo/QA bundle through a reviewed PR. The approved
Demo/QA retention exception does not satisfy the production Object Lock gate.
