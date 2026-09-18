# M31.5 Release Hardening and Reproducibility

Status: in progress. This branch is based on product `main` at
`5aa735c7b09dfa46cfab8ca5d9d725039d4b982e1`. It is a focused hardening branch
and does not modify PR #151 or PR #147.

## Baseline and SHA reconciliation

The product baseline is frozen at:

`5aa735c7b09dfa46cfab8ca5d9d725039d4b982e`

The M31.4 handoff is versioned on the validation branch rather than on this
product baseline. Its SHA audit found two malformed references, corrected here
without changing PR #151:

| Context | Malformed reference | Correct full object |
| --- | --- | --- |
| post-merge product main | `5aa735c7b09dfa46cfab8ca5d9d725039d4b982e1` | `5aa735c7b09dfa46cfab8ca5d9d725039d4b982e` |
| validated notification-teardown harness | `84e2bafb095ec085e04ae8fb039eba0c98aa3ff` | `84e2bafb095ec085e04ae8fb039eba0c98aa3ff0` |

Short refs in the historical handoff are retained as intentional abbreviated
refs where they resolve uniquely; they are not treated as full SHA values.

## Dependency audit input

`requirements.txt` is the canonical, reviewed input for `pip-audit`. It covers
the non-stdlib packages imported by repository-owned Python code and does not
pretend to replace the pinned Odoo runtime image. The runtime image and
PostgreSQL/Alpine/Nginx images remain governed by
`deployment/runtime/runtime-lock.json`.

The expected security-audit state after the new input is explicit:

- `PASS_NO_FINDINGS` if pip-audit reports no vulnerabilities;
- `FINDINGS_UNTRIAGED` if it reports vulnerabilities;
- `ERROR/BLOCKED` if the tool or evidence classifier fails.

`NOT_EXECUTED` is no longer an acceptable result once this branch's security
workflow runs successfully.

## M31.4 limitation inventory and release scope

The first stable-release proposal includes the accepted M31.4 scope: role and
direct authorization, Configuration boundaries, protected data, permitted and
prohibited mutations, company isolation, keyboard/focus/responsive coverage,
Mission16, Mission23 and authorized ORM teardown.

The following remain outside the first stable release and require separate
follow-up evidence: duplicate notification detection; SMTP/email delivery;
workflow authorization without a supported real transition; cancellation
specific cleanup; and any pip-audit findings requiring remediation.

## Reproducibility gate

The release candidate must be reproducible from a clean clone and the frozen
baseline through provision, bootstrap, license issuance/activation, customer
initialization, module update, backup/restore, rollback and cleanup. The gate
must also verify the runtime lock, package input, lockfiles, release manifest,
and rollback identity. No release or tag is created by M31.5.

## Version and operational documentation proposal

Proposed first stable product version: `1.0.0`, subject to Product Owner
authorization after all hardening gates pass. Until then the proposal is not a
release and no tag is created. Installation follows `docs/DEPLOYMENT.md` and
customer upgrades/rollback follow `docs/CUSTOMER_UPGRADE_RUNBOOK.md`; those
runbooks remain the operational authority for bundle identity, backups,
runtime-lock approval and automatic rollback.
