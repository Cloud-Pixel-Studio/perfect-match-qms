# PMQMS AWS IAM Model for External License Authority

This is a preparatory design. It does not create AWS resources or contain
credentials.

## Resources

- Dedicated KMS CMK for the authority secret.
- Secrets Manager secret for the Ed25519 PEM, one secret per authority.
- Private S3 bucket for encrypted recovery artifacts, with versioning and
  Object Lock.
- CloudTrail management events for Secrets Manager and KMS, plus S3 data
  events for backup objects under the exact recovery prefix.

Suggested secret name:

```text
pmqms/license-authority/demo-qa/pmqms-demo-2026-v3
```

The actual ARN and account are administrator-owned configuration and must not
be committed here.

This Object Lock requirement is mandatory for production customer issuance.
The Product Owner-approved Demo/QA exception and its compensating controls are
specific to the existing Demo/QA authority and are documented in ADR-077 and
`docs/PMQMS_LICENSE_BACKUP_RECOVERY.md`; they do not relax the production
requirement.

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

- `s3:GetObjectVersion` on the exact locked backup prefix for versioned
  recovery;
- `s3:GetObject` on the exact locked backup prefix. The S3 `HeadObject` API is
  authorized by `s3:GetObject`; `s3:HeadObject` is not an IAM action;
- `kms:Decrypt` on the exact backup CMK;
- `secretsmanager:PutSecretValue` on the exact authority secret only during an
  approved recovery procedure.

The recovery role also needs the following narrowly scoped permissions on the
authority CMK that encrypts that exact secret, conditioned on the Secrets
Manager service and the exact secret ARN encryption context:

- `kms:GenerateDataKey`;
- `kms:Decrypt`.

These permissions are for restoring the secret value only. The recovery role
must not have issuance automation, `secretsmanager:DeleteSecret`,
`kms:ScheduleKeyDeletion`, or `kms:RotateKey`.

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
- CloudTrail management-event evidence for Secrets Manager/KMS calls and data-
  event evidence for S3 backup object operations;
- successful denied-access tests for issuer and audit roles;
- MFA and dual-approval evidence.
