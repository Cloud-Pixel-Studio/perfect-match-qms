# Customer Deployment Runbook

This runbook is for an authorized operator on the deployment host. It does not
replace DNS, certificate, customer identity, or licensing approval procedures.

## 1. Build the approved bundle

Run from a clean checkout at the approved release tag. The release tag and
customer bundle are explicit inputs; do not rely on a deployment default.

```bash
RELEASE_TAG=<APPROVED_RELEASE_TAG>
BUNDLE_PATH=<APPROVED_CUSTOMER_BUNDLE>
./deployment/scripts/customer-instance.sh bundle \
  --release "$RELEASE_TAG" \
  --output "$BUNDLE_PATH"
```

The command writes a self-identifying manifest and SHA-256 sidecar. The
manifest's product version, source commit, runtime lock, and safety flags are
authoritative for the customer artifact. The bundle is rejected if its tag,
checksums, runtime lock, or safety metadata do not agree.

## 2. Initialize an instance

Choose a unique slug and loopback port. Do not use `admin/admin`.

```bash
./deployment/scripts/customer-instance.sh provision northstar-precision \
  --type customer \
  --bundle "$BUNDLE_PATH"
./deployment/scripts/customer-instance.sh config northstar-precision
./deployment/scripts/customer-instance.sh bootstrap northstar-precision
```

Provision validates the complete bundle before creating the instance, then
derives and persists `product_version` and `source_release_sha` from the
validated product manifest. A supplied bundle cannot be silently overridden by
an environment release default. The command creates fresh PostgreSQL, Odoo
master, and initial technical admin secrets. Secrets remain outside Git and
are not printed by deployment commands. Use `credentials <slug>` only when
local operator access is required.

The `bootstrap` step installs the approved QMS module set in the empty
instance and must succeed before a commercial license exists. At this point
`license-status` is expected to report `missing`, and `activation-request`
may be run to produce the persisted environment identity for licensing. This
step does not create an operational customer organization, site, or named QMS
user, so it does not consume commercial capacity. `bootstrap-customer` remains
blocked until a signed license has been imported.

## 3. Offline activation

```bash
./deployment/scripts/customer-instance.sh activation-request northstar-precision
# Send activation/activation-request.json to an authorized licensing operator.
./deployment/scripts/customer-instance.sh import-license northstar-precision /secure/path/customer.pmql
./deployment/scripts/customer-instance.sh license-status northstar-precision
```

The license must be signed by an approved authority, match the persisted
environment ID, and provide company, site, and named-user capacity.

## 4. Bootstrap the customer

The first user consumes a named-user seat and receives the QMS Quality Manager
role. It is not an Odoo System Administrator.

```bash
./deployment/scripts/customer-instance.sh bootstrap-customer northstar-precision \
  --company-name 'Northstar Precision Components, Inc.' \
  --company-code NORTHSTAR \
  --user-login quality.manager@northstar.example \
  --user-name 'Northstar Quality Manager'
./deployment/scripts/customer-instance.sh create-site northstar-precision \
  --code NORTHSTAR-HQ --name 'Northstar Headquarters' --type headquarters
./deployment/scripts/customer-instance.sh customer-ready northstar-precision
```

The generated Quality Manager password is available only through the local
credentials mechanism. Rotate it through the normal Odoo user security flow.
The customer Quality Manager is not an Odoo System Administrator; platform
maintenance remains with the technical operator using the existing secrets
mechanism.

## 5. HTTPS and handoff

Create a DNS record for the customer domain, install the matching Nginx server
block from `deployment/nginx/customer.conf.example`, obtain a valid certificate,
reload Nginx, and confirm HTTP redirects to HTTPS. Never expose the database
manager or a database selector publicly.

Complete `docs/CUSTOMER_HANDOFF_CHECKLIST.md` and provide the customer with the
domain, release, license ID, limits, Quality Manager identity, health result,
and backup validation result. Do not include passwords.
