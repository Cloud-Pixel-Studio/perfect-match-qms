# PMQMS AWS IAM Model for External License Authority

This is a preparatory design. It does not create AWS resources or contain
credentials.

## Resources

- Dedicated KMS CMK for the authority secret.
- Secrets Manager secret for the Ed25519 PEM, one secret per authority.
- Private S3 bucket for encrypted recovery artifacts, with versioning and
  Object Lock.
- CloudTrail data events for Secrets Manager, KMS, and the backup prefix.

Suggested secret name:

```text
pmqms/license-authority/demo-qa/pmqms-demo-2026-v3
```

The actual ARN and account are administrator-owned configuration and must not
be committed here.

## Roles

### `PMQMSLicenseIssuer`

Allow only on exact resource ARNs:

- `secretsmanager:GetSecretValue`
- `secretsmanager:DescribeSecret`
- `kms:Decrypt` on the authority CMK, conditioned on the Secrets Manager
  service and approved region
- `s3:PutObject` and `s3:PutObjectTagging` only for sanitized issuance evidence,
  if evidence storage is required

The role must not rotate, delete, overwrite, list broadly, administer IAM,
access customer databases, or connect to customer VMs.

### `PMQMSLicenseRecovery`

Allow only:

- `s3:GetObject` and `s3:HeadObject` on the exact locked backup prefix;
- `kms:Decrypt` on the backup CMK;
- `secretsmanager:PutSecretValue` on the exact authority secret only during an
  approved recovery procedure.

Recovery must require MFA and two-person approval. It must not automatically
issue a license.

### `PMQMSLicenseAudit`

Read-only access to CloudTrail events and resource metadata. It must not read
the private secret or decrypt backup contents.

## Required deny boundaries

- No public S3 access.
- No wildcard secret, KMS, or IAM permissions.
- No `iam:PassRole` for issuer operators.
- No CI, GitHub, Docker, or customer VM access.
- No deletion without a separate break-glass role and retention controls.

## Evidence required from the administrator

- policy JSON review;
- CMK key policy review;
- secret resource policy review;
- S3 bucket policy, versioning, and Object Lock evidence;
- CloudTrail event evidence;
- successful denied-access tests for issuer and audit roles;
- MFA and dual-approval evidence.
