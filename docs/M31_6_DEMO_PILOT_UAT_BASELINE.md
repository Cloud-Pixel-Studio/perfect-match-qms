# Demo Pilot UAT Baseline

Date: 2026-09-21

Status: READY WITH LIMITATIONS

This baseline records the reproducible read-only validation of the isolated
Demo environment. It is not a production certification and does not certify
cross-company isolation.

## Immutable baseline

- Repository: `Cloud-Pixel-Studio/perfect-match-qms`
- GitHub `origin/main`: `c249d840b33e1ff8e842cc88d88d3c9538945dea`
- VM checkout: `c249d840b33e1ff8e842cc88d88d3c9538945dea`
- Database: `pmqms_demo`
- Demo URL: `http://192.168.68.151:8170/web/login?db=pmqms_demo`
- Odoo image: `odoo:19.0@sha256:94a4f480b8039dc9ca2bca9e77e59f97d3311f66e2aad663cf2670be9c66d4ea`
- PostgreSQL image: `postgres:15@sha256:0dda651c259bfe50e2bcc28ca23d1fcca772fa90b0210803aa7b97379ccf4e85`
- Runtime verification: PASS
- Health: PASS, HTTP 200; PostgreSQL healthy
- Validate Demo: PASS

## License and seed evidence

- License state: valid
- Capacity: 1 company, 3 sites, 7 named users
- Seed: PASS and idempotent
- Canonical records: 2 confirmed Cost of Quality events, 6 canonical cost
  lines, 22 Action Center values, and 7 fictional people
- No license, key, credential, seed, volume, or existing Demo record was
  changed during this baseline.

## Role matrix

Each role authenticated successfully using the existing local credential
mechanism. Logins and passwords are intentionally excluded from this
document. ORM checks used each functional user's context and did not use
`sudo`.

| Role | Login | Read-only UAT result | Observed scope |
| --- | --- | --- | --- |
| Quality Manager | PASS | PASS | 3 sites, all seeded QMS surfaces |
| Quality Supervisor | PASS | PASS | 1 site, 24 processes, scoped records |
| Document Controller | PASS | PASS | 3 sites, 6 documents |
| Internal Auditor | PASS | PASS | 3 sites, audit/evidence surfaces |
| Process Owner | PASS | PASS | 2 sites, 7 processes, scoped records |
| Management User | PASS | PASS | 3 sites, read-oriented management visibility |
| QMS Viewer | PASS | PASS | 3 sites, read-only visibility |

The read checks covered organization, sites, processes, documents, risks,
CAPA, audits, and Action Center records. Counts were read after applying the
functional user's record rules.

## Management User contract

Using the authenticated Management User context:

- Risk, CAPA, and CAPA action reads: PASS.
- `create`, `write`, and `unlink` on those models: rejected server-side.
- `action_start` and `action_complete` on CAPA actions: rejected with
  `AccessError`.
- Dashboard/Action Center and management read surfaces remained available.
- Action checks ran in savepoints; no mutation was committed.
- A subsequent `validate-demo` remained PASS with unchanged canonical counts.

## Backup and cleanup

The most recent Demo-only backup, created before the post-merge update, is:

`/opt/perfect-match/backups/odoo-demo/pmqms_demo-20260921T002448Z.tar.gz`

The archive exists and was retained. No volumes were removed. Temporary UAT
files were removed after execution, and no credentials, hashes, cookies,
private keys, databases, filestores, or raw traces were added to Git.

## Warnings and limitations

Expected seed warnings were limited to protected workflow operations that are
not authorized for the seeding context. They did not prevent seed,
validation, health, or role read checks.

The following remain outside this single-company baseline:

- Cross-company isolation: NOT TESTED; requires a separate disposable
  multi-company fixture.
- Browser visual/menu walkthrough for every role: not part of this ORM/read-
  only baseline.
- Email/SMTP delivery and workflow-transition certification are not inferred
  from this baseline.

## Reproduction sequence

From the VM checkout at the recorded HEAD, use the official deployment script
only: `runtime-verify`, `ps`, `health`, `validate-demo`, and the existing
credential mechanism. Create a Demo-only backup before any update. Do not use
`reset-demo`, remove volumes, reissue the license, or expose credential
contents.

### Role-check sequence

The role evidence is an authenticated ORM check, not an inference from
startup, login, or `validate-demo`. Repeat it with one fresh session per
persona, obtaining the persona names and login identifiers only from
`./deployment/scripts/odoo-demo.sh credentials` or the ORM. Never print the
password files.

For each persona, the check sequence is:

1. Authenticate with that persona's existing credential file.
2. In that authenticated user context (without `sudo`), read each of
   `pm.qms.organization`, `pm.qms.site`, `pm.qms.process`,
   `pm.qms.document`, `pm.qms.risk`, `pm.qms.capa`, `pm.qms.audit`, and
   `pm.qms.action.center.line`; record only boolean success and sanitized
   record counts.
3. For Management User, read risks, CAPA, and CAPA actions, then execute
   `check_access` for `create`, `write`, and `unlink`, and call
   `action_start` and `action_complete` inside rolled-back savepoints. The
   expected result for each mutation/action is `AccessError`; the read result
   must remain successful.
4. Run `./deployment/scripts/odoo-demo.sh validate-demo` again and compare
   canonical counts to the pre-check snapshot. Any count change is a failed
   cleanup/mutation result, not a PASS.

The recorded run used seven separate authenticated contexts and produced the
role matrix above. This repository does not contain a checked-in credential
or raw-trace harness; the sequence above is the exact sanitized operator
procedure used for this baseline.
