# Customer Upgrade Runbook

Customer environments run an explicit approved Perfect Match release. They do
not pull `main`, feature branches, or arbitrary dirty worktrees.

1. Confirm the target release tag and compatibility notes.
2. Confirm customer maintenance approval and available recovery storage.
3. Run `customer-instance.sh backup <slug>` and verify its SHA-256 file.
4. Build or obtain the target customer bundle and verify its manifest/checksum.
5. Run `customer-instance.sh upgrade <slug> --to <release-tag>`.
6. Deploy the approved bundle into the instance runtime.
7. Run the controlled module update/bootstrap command and `health <slug>`.
8. Run `license-status`, `customer-ready`, and the customer smoke checklist.
9. Record previous/current versions and deployment date in the manifest.

If backup, release verification, module update, or health validation fails,
stop. Restore the verified pre-upgrade backup using the recovery runbook. A
database migration may require restore-based rollback; application image
replacement alone is not a rollback guarantee.
