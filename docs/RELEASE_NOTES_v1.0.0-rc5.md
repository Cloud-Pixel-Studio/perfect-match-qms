# Perfect Match QMS v1.0.0-rc5

## Operational Intelligence & Full Product Demo Release Candidate

Release candidate date: 2026-08-23

`v1.0.0-rc5` freezes the current reusable Perfect Match QMS product baseline
after Mission 17 and the dedicated Full Product Demo environment. It is a
pre-release candidate for technical validation, product review, demonstration,
training, and documentation.

Readiness and operational metrics support QMS work; they do not constitute
certification, certification-body approval, guaranteed compliance, or certified
software.

## Highlights

### Mission 17: Operational Intelligence

- Unified Action Center with source-authoritative aggregation from supported QMS
  records.
- My Actions, organization-allowed actions, overdue, due-today, due-soon, open,
  and no-due-date views.
- Action Center source navigation back to the originating risk, NCR, CAPA,
  audit, training, qualification, calibration, complaint, 8D, supplier issue,
  SCAR, or management-review action.
- Cost of Quality records with Prevention, Appraisal, Internal Failure, and
  External Failure categories.
- Recoveries, Gross Quality Cost, COPQ, and Net Quality Cost calculations.
- Cost Events and Cost Analytics views with dashboard and Management Review
  integration.
- Source alignment and idempotent refresh protections so operational records
  remain authoritative and Action Center rows are not fabricated.

### Full Product Demo Environment

- Dedicated isolated `pmqms_demo` database, containers, filestore, and secrets.
- Dedicated `deployment/scripts/odoo-demo.sh` install, update, seed, validate,
  health, credentials, and reset-protection commands.
- Fictional Apex Precision Systems, Inc. company with realistic interconnected
  examples across the current customer-facing QMS surface.
- Idempotent demo seeding with workflow-aware source records for documents,
  evidence, risks, NCR, CAPA, audits, people, training, qualifications,
  calibration, customer quality, supplier quality, Action Center, Cost of
  Quality, and Management Review.
- Demo Guide and Demo Coverage Matrix documenting menu paths, records,
  scenarios, and coverage status.
- Perfect Match brand treatment using the approved primary logo and operational
  blue, magenta, green, and white visual language.

## Product Baseline

The release includes the current QMS stack:

- Application shell and executive dashboard
- Guided Implementation and Readiness Center
- Documents and Evidence
- Risks, NCR, and CAPA
- Internal Audit
- Objectives, KPI, and customer/supplier performance
- Management Review
- People, Training, Competency, Qualifications, and Acknowledgments
- Equipment, Calibration, and Out-of-Tolerance Impact Assessment
- Customer Complaints, Quality Alerts, 8D, Supplier Issues, and SCAR
- Unified Action Center
- Cost of Quality and COPQ analytics
- Full Product Demo Environment

## Validation Summary

Canonical source before release documentation:

```text
ec70efb4b8df7b2ace5b1601263638b097008004
```

DEV validation passed before release preparation:

- DEV Compose configuration: PASS
- Existing `pmqms_dev` update through Mission 17: PASS
- DEV HTTP health: `302` (Odoo login redirect)
- Clean `pmqms_test` installation with the complete current stack: PASS
- Odoo Mission 17 regression: 120 post-tests, 0 failures, 0 errors
- Standalone dependency gate: PASS; no functional dependency on Sales, Purchase,
  Inventory, MRP, HR, Accounting, Quality, or Maintenance
- Python compile, manifests/XML, secret scan, content safety, shell syntax, and
  Git diff checks: PASS

GitHub CI, final main merge, Demo deployment, browser validation, and the
annotated release tag are recorded in the final release evidence after those
checkpoints complete.

## Demo Validation Contract

The Demo is updated only from merged canonical `main`. The release process must
confirm:

- `pmqms_demo` HTTP health is `200` through the public reverse-proxy URL.
- `validate-demo` passes.
- Seed/update is idempotent when run twice.
- Action Center rows come from authoritative source records.
- Cost Analytics reports gross cost, COPQ, recoveries, and net quality cost.
- Demo Guide and Demo Coverage Matrix remain current.

## Frozen Pilot

The Oliva Torras pilot database `pmqms_oliva_pilot` remains frozen and is not
part of RC5 validation. No Oliva update, seed, backup, or functional validation
is performed for this release.

## Limitations

- RC5 is a release candidate, not the final stable `v1.0.0` release.
- Licensing, entitlement enforcement, ERP integrations, optional connectors,
  and Mission 18 are outside this release.
- Future standards mappings remain reference metadata only; copyrighted
  external-standard requirement text is not included.
