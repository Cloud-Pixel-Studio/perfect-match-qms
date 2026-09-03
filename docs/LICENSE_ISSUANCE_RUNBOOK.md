# License Issuance and Replacement Runbook

This runbook is for Perfect Match operators. Never paste a private key,
customer password, API key, or full activation payload into GitHub, a
project-management system, logs, or screenshots.

## Issue a license

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

The issuer defaults to `key_id=pmqms-license-2026`. Use an explicit historical
key ID only for approved compatibility or verification work. The historical
`pmqms-demo-2026` public verifier remains registered so previously issued
licenses continue to validate.

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

Add the new public key under a new `key_id` before issuing with it. Generate
the private key directly in the external operator secret store with mode
`0600`; never copy it to Git, a bundle, a Docker image, or a customer
instance. Retain old public keys while valid customer licenses remain in
circulation. Back up the external environment identity together with the
deployment secrets. A server migration keeps the identity and license; a
deliberately new installation gets a new identity and a newly issued license.
