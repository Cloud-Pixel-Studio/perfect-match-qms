# PMQMS License Authority Backup and Recovery

## Backup requirements

The private authority key must be backed up outside Git, Docker, CI, and all
customer VMs.

1. Encrypt the backup before storage or use the approved KMS-encrypted S3
   object path.
2. Production backups must use a private, versioned S3 bucket with Object Lock.
   No production customer license may be issued until this is available.
3. Store the key fingerprint and authority metadata separately from the secret
   contents.
4. Record the backup version, creation time, custodians, and retention date.
5. Never put the plaintext PEM in logs or ordinary VM backups.

## Recovery rehearsal

An AWS administrator and a second approver must:

1. authorize recovery;
2. retrieve one exact object version;
3. decrypt it in an ephemeral controlled workspace;
4. verify the Ed25519 public fingerprint;
5. compare it with the recorded fingerprint;
6. restore the secret only if the primary value is unavailable or corrupt;
7. perform a non-customer test signing operation;
8. destroy the ephemeral plaintext material;
9. retain sanitized evidence only.

Recovery does not authorize a license issue by itself. The normal issuance
review remains mandatory.

## Approved Demo/QA exception

The Product Owner approved a narrowly scoped Demo/QA exception because the
current Demo/QA backup bucket does not have Object Lock. This is not a
production control and must not be used to issue production customer licenses.
The compensating controls for Demo/QA are:

- S3 versioning and complete public-access blocking;
- SSE-KMS with the dedicated PMQMS backup CMK;
- age encryption of backup contents before upload;
- an issuer identity without S3 object-delete permission and a separate
  recovery identity;
- CloudTrail auditing for authority management and backup access;
- backup object names and exact S3 versions recorded in custody metadata;
- periodic restoration tests, with the restored public fingerprint verified;
- dual approval for recovery; and
- quarterly integrity review.

The exception applies only to Demo/QA. Object Lock remains mandatory for
production backups. If any compensating control is unavailable or fails, stop
Demo/QA authority operations and report `BLOCKED` until restored.

## Failure conditions

Stop if the fingerprint differs, the object version is ambiguous, required
retention or an explicitly approved Demo/QA exception is absent, the approver
is unavailable, or the plaintext key appears in an unauthorized location.
Report `BLOCKED`; do not generate a replacement key in a VM.
