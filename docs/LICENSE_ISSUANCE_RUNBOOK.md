# License Issuance and Replacement Runbook

This runbook is for Perfect Match operators. Never paste a private key,
customer password, API key, or full activation payload into GitHub, a
project-management system, logs, or screenshots.

## Issue a license

Issuance is permitted only from an approved external authority store. The
preparatory implementation in this repository does not create that store and
does not generate a key.

1. Read the target environment UUID from its external secret/configuration
   file. Do not copy the database UUID because it is not authoritative.
2. Use the active Ed25519 private PEM key stored outside the repository and
customer instances:

```text
/opt/perfect-match/secrets/license-authority/pmqms-license-2026.pem
```

3. Run `deployment/scripts/issue-license.py` with the environment UUID,
   customer, edition, revision, and limits. The command writes a `.pmql` file
   and prints only a safe summary.
4. Transfer the `.pmql` file to the target secret directory with owner-only
   permissions. Keep the private key only in the license-authority secret store.

Example shape (use the real target identity and values at run time):

```bash
python3 deployment/scripts/issue-license.py \
  --private-key /opt/perfect-match/secrets/license-authority/pmqms-license-2026.pem \
  --output /opt/perfect-match/operator-licenses/customer.pmql \
  --environment-id "<target-environment-uuid>" \
  --customer-name "Fictional Customer Organization" \
  --license-id PMQMS-CUSTOMER-2026 \
  --revision 1 --company-limit 1 --site-limit 3 --named-user-limit 8
```

The issuer defaults to `key_id=pmqms-license-2026`. The preparatory issuer
accepts the reserved future Demo/QA v3 identifier with `--key-id pmqms-demo-2026-v3
--deployment-scope demo-qa` only after the external store, fingerprint,
backup recovery, and Product Owner approval are complete. The signed scope is
required. Issuance support does not register or trust v3: the Demo/QA importer
uses a dedicated read-only registry mounted at
`/run/pmqms-demo-qa-public-keys.json`. The standard customer bundle removes
the Demo/QA importer and registry, so it rejects Demo/QA-only authorities.
Never copy a Demo/QA private key to Git, Docker, CI, or a target VM.

## Blocked state

If the authority secret, verified fingerprint, or recovery evidence is absent:

1. Do not generate a replacement key in a VM.
2. Do not issue a synthetic or unsigned `.pmql`.
3. Do not reuse a license for another environment UUID.
4. Leave the target unlicensed and record `BLOCKED`.
5. Escalate to the AWS administrator and license custodian.

Demo2 remains blocked under these rules until a signed license is delivered
through the approved channel.

## Import and replacement

Run `./deployment/scripts/odoo-demo.sh provision-license` for Demo or
`./deployment/scripts/odoo-dev.sh provision-license` for DEV. The application
validates signature, key, schema, dates, environment, and revision before
import. A replacement marks the old row non-current and creates the new row in
the same transaction. Invalid documents and older/equal revisions leave the
current license unchanged.

For an offline customer, use the Commercial License screen and the activation
request action. Send the generated request through the approved support
channel, receive the signed `.pmql`, and use Import Updated License. No
Internet connection is required by the runtime.

## Rotation and migration

Rotation is additive. After approval, generate v3 directly in the external
authority store, verify the public fingerprint, create and restore an encrypted
backup, and then submit a separate PR containing only the public key and
documentation. Retain all prior public keys while valid licenses remain in
circulation. Do not issue a v3 `.pmql` before that PR is reviewed and merged.

See `docs/PMQMS_LICENSE_BACKUP_RECOVERY.md` for recovery evidence and
`docs/PMQMS_CLIENT_INSTALL_LICENSE_CHECKLIST.md` for target installation.
