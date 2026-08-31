# License Issuance and Replacement Runbook

This runbook is for Perfect Match operators. Never paste a private key,
customer password, API key, or full activation payload into GitHub, a
project-management system, logs, or screenshots.

## Issue a license

1. Read the target environment UUID from its external secret/configuration
   file. Do not copy the database UUID because it is not authoritative.
2. Use an Ed25519 private PEM key stored outside the repository:

```text
/opt/perfect-match/secrets/license-authority/signing-key.pem
```

3. Run `deployment/scripts/issue-license.py` with the environment UUID,
   customer, edition, revision, and limits. The command writes a `.pmql` file
   and prints only a safe summary.
4. Transfer the `.pmql` file to the target secret directory with owner-only
   permissions. Keep the private key only in the license-authority secret store.

Example shape (use the real secret path and values at run time):

```bash
python3 deployment/scripts/issue-license.py \
  --private-key /opt/perfect-match/secrets/license-authority/signing-key.pem \
  --output /opt/perfect-match/secrets/odoo-demo/demo_license.pmql \
  --environment-id "<target-environment-uuid>" \
  --customer-name "Apex Precision Systems, Inc." \
  --license-id PMQMS-DEMO-2026 \
  --revision 1 --company-limit 1 --site-limit 3 --named-user-limit 8
```

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

Add the new public key under a new `key_id` before issuing with it. Retain old
public keys while valid customer licenses remain in circulation. Back up the
external environment identity together with the deployment secrets. A server
migration keeps the identity and license; a deliberately new installation gets
a new identity and a newly issued license.
