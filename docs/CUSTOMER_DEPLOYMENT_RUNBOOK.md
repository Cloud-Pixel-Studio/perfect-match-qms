# Customer Deployment Runbook

This runbook is for an authorized operator on the deployment host. It does not
replace DNS, certificate, customer identity, or licensing approval procedures.

## 1. Build the approved bundle

Run from a clean checkout at an approved tag:

```bash
./deployment/scripts/customer-instance.sh bundle \
  --release v1.0.0-rc7 \
  --output /opt/perfect-match/bundles/perfect-match-qms-v1.0.0-rc7-customer.tar.gz
```

The command writes a manifest and SHA-256 file and rejects Demo identifiers,
private key paths, and forbidden bundle paths.

## 2. Initialize an instance

Choose a unique slug and loopback port. Do not use `admin/admin`.

```bash
./deployment/scripts/customer-instance.sh provision northstar-precision \
  --type customer \
  --bundle /opt/perfect-match/bundles/perfect-match-qms-v1.0.0-rc7-customer.tar.gz
./deployment/scripts/customer-instance.sh config northstar-precision
./deployment/scripts/customer-instance.sh bootstrap northstar-precision
```

The command creates fresh PostgreSQL, Odoo master, and initial technical admin
secrets. Secrets remain outside Git and are not printed by deployment commands.
Use `credentials <slug>` only when local operator access is required.

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

## 5. HTTPS and handoff

Create a DNS record for the customer domain, install the matching Nginx server
block from `deployment/nginx/customer.conf.example`, obtain a valid certificate,
reload Nginx, and confirm HTTP redirects to HTTPS. Never expose the database
manager or a database selector publicly.

Complete `docs/CUSTOMER_HANDOFF_CHECKLIST.md` and provide the customer with the
domain, release, license ID, limits, Quality Manager identity, health result,
and backup validation result. Do not include passwords.
