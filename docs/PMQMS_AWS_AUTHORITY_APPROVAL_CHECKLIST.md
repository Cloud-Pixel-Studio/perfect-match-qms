# PMQMS AWS Authority Approval Checklist

The checklist must be completed by an AWS administrator before generating
`pmqms-demo-2026-v3`. No key generation is authorized by this document.

## Infrastructure

- [ ] Dedicated KMS CMK created and deletion protection configured.
- [ ] Secrets Manager secret created with the exact authority scope.
- [ ] Private S3 backup bucket created in the approved account and region.
- [ ] S3 versioning enabled.
- [ ] S3 Object Lock and retention policy enabled.
- [ ] Public access blocked.
- [ ] CloudTrail enabled for secret, KMS, and backup events.

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

`pmqms-demo-2026-v3` is **NOT GENERATED**. The project remains blocked until
all administrator-only items above are evidenced.
