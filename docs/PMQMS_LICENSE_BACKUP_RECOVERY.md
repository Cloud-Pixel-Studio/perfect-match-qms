# PMQMS License Authority Backup and Recovery

## Backup requirements

The private authority key must be backed up outside Git, Docker, CI, and all
customer VMs.

1. Encrypt the backup before storage or use the approved KMS-encrypted S3
   object path.
2. Store it in a private, versioned S3 bucket with Object Lock.
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

## Failure conditions

Stop if the fingerprint differs, the object version is ambiguous, retention
is missing, the approver is unavailable, or the plaintext key appears in an
unauthorized location. Report `BLOCKED`; do not generate a replacement key in
a VM.
