# Release Baseline v1.0.0-rc5

Release: `v1.0.0-rc5`

Release date: 2026-08-23

Release type: Operational intelligence and full product demo release candidate

## Source Baseline

The synchronized canonical `main` source before RC5 documentation was:

```text
ec70efb4b8df7b2ace5b1601263638b097008004
```

The final release tag must target the final merged `main` commit. The tag target
and final main SHA are verified again immediately before publication.

Canonical repository:

```text
https://github.com/Cloud-Pixel-Studio/perfect-match-qms
```

## Lifecycle

Perfect Match QMS follows this release lifecycle:

```text
DEV validation -> pull request -> GitHub CI -> merge to main
  -> update Perfect Match Demo -> functional and visual validation
  -> annotated release tag and GitHub pre-release
```

DEV is the engineering and automated-validation environment. `main` is the
canonical approved source. The dedicated Demo is the canonical functional and
product-validation environment.

The Oliva Torras pilot is frozen and is not part of the RC5 validation cycle.

## Product Scope

RC5 freezes the current reusable QMS product containing:

- Perfect Match application shell and executive dashboard
- Guided Implementation, framework packs, activities, evidence, gaps, and
  Readiness Center
- Document control, revisions, Evidence, Risks, NCR, CAPA, and Internal Audit
- Objectives, KPI, customer/supplier performance, and Management Review
- People, Training, Competency, Qualifications, and document Acknowledgments
- Equipment, Calibration, Out-of-Tolerance Impact Assessment, and traceability
- Customer Complaints, Quality Alerts, 8D, Supplier Issues, and SCAR
- Source-authoritative Unified Action Center
- Cost of Quality, COPQ, recoveries, and Cost Analytics
- Dedicated fictional Full Product Demo Environment

## Quality Gate Evidence

Validation was executed from the clean synchronized baseline before release
documentation:

- Python compile: PASS
- Addon manifests and XML: PASS
- Secret scan: PASS
- External-standard content safety: PASS
- Shell syntax: PASS
- Git diff check: PASS
- DEV Docker Compose configuration: PASS
- Existing DEV database update through Mission 17: PASS
- DEV HTTP health: `302` login redirect
- Fresh clean `pmqms_test` installation: PASS
- Upgrade validation through Mission 17: PASS
- Odoo Mission 17 regression: 120 tests, 0 failures, 0 errors
- Standalone product architecture gate: PASS

The repository's current functional addons have no dependency on Odoo Sales,
Purchase, Inventory, MRP, HR, Accounting, Quality, or Maintenance. The QMS
runtime uses Odoo as its platform and keeps QMS lifecycle state in QMS addons.

## Demo Baseline

| Item | Value |
| --- | --- |
| Database | `pmqms_demo` |
| Public URL | `https://demo.invperfectmatch.com/web/login?db=pmqms_demo` |
| Internal URL | `http://192.168.68.151:8170/web/login?db=pmqms_demo` |
| Company | Apex Precision Systems, Inc. |
| Source policy | Merged canonical `main` only |
| Oliva pilot | Frozen and untouched |

The Demo Coverage Matrix and Demo Guide are the authoritative product-tour
references for customer-facing feature examples. The release gate requires
Demo update, validation, idempotent seed/update, HTTP `200`, and functional/UI
checks after the final main merge.

## Release Integrity

- RC1, RC2, RC3, and RC4 annotated tags remain immutable.
- RC5 must be absent before tag creation.
- RC5 must be an annotated tag targeting final `main`.
- No database dumps, filestores, customer data, secrets, credentials, or private
  keys are attached to the GitHub release.

## Non-Claims

Perfect Match QMS supports, assists, enables, records, and analyzes quality
management work. It does not claim guaranteed compliance, guaranteed
certification, certified software, or certification-body approval.
