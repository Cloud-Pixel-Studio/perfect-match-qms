# PMQMS Client License Installation Checklist

This checklist applies after an approved `.pmql` has been issued. It does not
authorize key generation or license issuance.

## Before transfer

- [ ] Target UUID was read from the target's official identity file.
- [ ] License UUID matches the target UUID exactly.
- [ ] Signature and public fingerprint verified.
- [ ] `key_id` is approved for the target bundle.
- [ ] Signed scope matches the target environment.
- [ ] Company, site, and named-user limits are approved.
- [ ] Dates and revision are valid.
- [ ] Artifact contains no private key or unrelated secret.

## Transfer and import

- [ ] Transfer only the `.pmql` file through the approved channel.
- [ ] Store it in the official protected license directory.
- [ ] Apply owner-only permissions (`0600`).
- [ ] Run the official import/provision command.
- [ ] Verify the active license status and UUID.
- [ ] Keep the prior license until replacement validation completes.

## Post-installation

- [ ] Runtime health passes.
- [ ] No other environment volumes, networks, databases, or secrets were
      touched.
- [ ] Backup is created before any subsequent data operation.
- [ ] Seed and validation are run only when explicitly authorized.
- [ ] Secrets and raw license contents are excluded from logs and artifacts.

If any check fails, stop and report the exact sanitized failure. Never use a
license issued for another UUID.
