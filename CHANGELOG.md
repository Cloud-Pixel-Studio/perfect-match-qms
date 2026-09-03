# Changelog

## Unreleased

- Added the external `pmqms-license-2026` issuance authority while retaining
  `pmqms-demo-2026` for historical license verification.
- Made operational process resolution idempotent when multiple framework
  controls share a source process, while preserving company and organization
  boundaries.

## 1.0.0-rc7 - 2026-08-23

- Froze the standalone Perfect Match QMS baseline after Mission 20 with signed
  offline licensing, environment binding, activation requests, atomic license
  replacement, revision protection, and commercial entitlement enforcement.
- Documented operational company, active Site, and active named-user capacity,
  including framework exclusion, archive/reactivation behavior, one-seat
  multi-role counting, and protected exemptions.
- Validated cryptographic tamper rejection, wrong-environment rejection,
  invalid replacement safety, Mission 19 security behavior, standalone
  installation/upgrade paths, and the isolated fictional Demo.
- Added the RC7 release notes and immutable release baseline documentation.
- RC7 does not include online licensing, billing, a customer installer, or
  Mission 21.

## 1.0.0-rc6 - 2026-08-23

- Established the standalone Perfect Match QMS organization and Site product
  foundation with the Apex three-site Demo contract.
- Added secure access, role, company, site, process-scope, equipment-scope,
  Action Center, and Cost of Quality validation coverage from Missions 18 and
  19.
- Retired the Oliva Torras pilot runtime after a final validated local backup;
  removed its active Compose files, scripts, database, volumes, network,
  secrets, and ports while preserving historical documentation and Plane
  traceability.
- Made DEV and Demo the only active validation lifecycle environments.
- Added RC6 release notes, baseline, and lifecycle ADR. Commercial licensing
  and Mission 20 remain outside this release.

## 1.0.0-rc5 - 2026-08-23

- Froze the current Perfect Match QMS baseline through Mission 17, including the
  Unified Action Center, source-authoritative actions, due-date buckets, and
  source navigation.
- Added Cost of Quality and COPQ with prevention, appraisal, internal failure,
  external failure, recoveries, gross cost, and net quality cost analytics.
- Included dashboard and Management Review integration for Action Center and
  Cost of Quality signals.
- Established the isolated `pmqms_demo` Full Product Demo Environment with
  dedicated containers, database, filestore, idempotent seed/update, validation,
  reset protection, fictional interconnected examples, and Perfect Match brand
  treatment.
- Updated the Demo Guide and Demo Coverage Matrix for the current customer-facing
  product surface.
- Validated the complete Mission 17 stack with 120 Odoo post-tests, 0 failures,
  0 errors, DEV update, clean installation, standalone dependency review, and
  release quality gates.
- Added RC5 release notes and release baseline documentation.

## 1.0.0-rc4 - 2026-08-22

- Added `pm_qms_customer_quality` with customer complaints, quality alerts, 8D cases, supplier issues, SCAR, supplier response history, and controlled closure workflows.
- Preserved NCR and CAPA as authoritative engines while linking customer and supplier quality records to them.
- Integrated customer and supplier quality signals into dashboard and management review.
- Fixed CAPA 5 Why inline list display so sequence, question, and answer columns are visible instead of a generic ID row.
- Validated the current stack with 110 Odoo post-tests, DEV install/update, GitHub Actions, and Oliva pilot-safe update/health checks.
- Added RC4 release notes, release baseline, and release work item.
- Recorded non-blocking GitHub Actions Node.js runtime warnings as release technical debt.

## 1.0.0-rc3 - 2026-08-21

- Added QMS People with people records, roles, competencies, competency matrix, assessments, training, qualifications, and revision-specific document acknowledgments.
- Added equipment, monitoring resources, calibration planning, calibration events, evidence traceability, due/overdue monitoring, out-of-tolerance workflow, quarantine, impact assessment, and NCR/CAPA traceability.
- Validated the operational expansion with 103 Odoo post-tests, GitHub Actions, and Oliva pilot-safe update/health checks.
- Added RC3 release notes and baseline documentation.

## 1.0.0-rc2 - 2026-08-21

- Added the Perfect Match QMS product application shell as the coherent user entry point for the current QMS baseline.
- Added the executive dashboard with implementation readiness, controls, activities, evidence, operational health, performance, and management review indicators.
- Added guided implementation UX with implementation areas, control guidance, gap visibility, readiness center, area progress, and deterministic recommended next actions.
- Added Perfect Match-specific Activities UX backed by Odoo `project.task`, preserving native Project for authorized users while keeping implementation work in QMS context.
- Integrated existing QMS operational modules into the application shell: documents, evidence, risk, NCR, CAPA, audit, objectives, KPI, customer performance, supplier performance, and management review.
- Preserved historical readiness snapshots and management review history as release baseline behavior.
- Validated `PM-QMS-QUALITY` version `1.0` in the Oliva Torras technical pilot with 6 implementation areas, 37 controls, 74 generated activities, and 37 required evidence expectations.
- Confirmed the Oliva pilot as validation-only data; no Oliva-specific product code, secrets, database dumps, filestore data, or customer production records are included.
- Added RC2 release notes and baseline documentation.
- Documented non-claims: no certification claim, no certification-body approval claim, no guaranteed compliance claim, and no copyrighted external-standard requirement text.
- Recorded non-blocking GitHub Actions Node.js 20 deprecation warning as release technical debt.

## 1.0.0-rc1 - 2026-08-15

- Added isolated Oliva Torras technical pilot deployment under
  `deployment/docker/pilot/` with dedicated database, network, volumes, secrets,
  localhost-only ports, and operational script `deployment/scripts/odoo-pilot.sh`.
- Added pilot backup and restore scripts for
  `/opt/perfect-match/backups/odoo-oliva-pilot`.
- Added `pm_qms_migration` with controlled manager-only document and evidence
  CSV import wizards.
- Blocked evidence migration from directly creating `accepted` evidence; review
  acceptance must use the QMS evidence workflow.
- Added Mission 10 DEV test target and CI coverage through `test-mission10`.
- Generated and validated the Oliva technical pilot project with 37 controls,
  74 generated tasks, and 37 required evidence expectations.
- Validated one labeled `PILOT VALIDATION` control end to end, improving
  readiness from 0.0000 percent to 2.7027 percent while preserving the earlier
  readiness snapshot.
- Added Oliva runbook, implementation guide, onboarding checklist, migration
  inventory template, release notes, plan, and ADRs.
- Documented explicit non-claims: no customer production go-live, no invented
  Oliva operational data, no certification claim, and zero approved external
  mapping coverage without a human-approved CSV.

## 0.8.0 - 2026-08-15

- Added `pm_qms_pack_quality` with the first commercial Perfect Match Quality
  Management Pack, code `PM-QMS-QUALITY`, version `1.0`.
- Seeded 37 proprietary quality-management controls, 74 implementation
  activities, and 37 mandatory evidence expectations.
- Added mapping profiles for external reference metadata, including the active
  `PM-QMS-QUALITY-ISO9001` profile for ISO 9001 edition metadata.
- Added CSV mapping import with all-row validation, approval metadata,
  duplicate protection, and rejection of external requirement text columns.
- Locked approved profile mappings against silent definition edits or deletion.
- Extended project generation so framework-pack controls can create equivalent
  client organization processes before creating control instances.
- Added external-standard content-safety scanning to CI and local validation.
- Extended DEV scripts and CI quality gate for Mission 09 validation.
- Added Mission 09 architecture, security, testing, plan, addon README, and
  ADR documentation.

## 0.7.0 - 2026-08-15

- Added `pm_qms_implementation` with versioned framework packs,
  pack-control relationships, implementation projects, implementation controls,
  Odoo project/task generation, readiness assessments, and generator wizard.
- Added multi-pack control deduplication and organization/control
  `pm.qms.control.instance` reuse.
- Added live readiness, evidence completion, and activity completion metrics,
  with not-applicable controls excluded from the readiness denominator.
- Added historical readiness assessment snapshots with immutable completed
  assessment items.
- Extended DEV scripts and CI quality gate for Mission 08 validation.
- Added Mission 08 architecture, security, testing, plan, addon README, and
  ADR documentation.

## 0.6.0 - 2026-08-15

- Added `pm_qms_management_review` with management review records, workflow,
  participants, period validation, decisions, and follow-up actions.
- Added historical management review input snapshots across objectives, KPIs,
  customer and supplier performance, audits, audit findings, risks,
  opportunities, NCR, CAPA, and previous review actions.
- Added snapshot locking policy so normal users cannot silently regenerate or
  mutate review history once a review is ready or completed.
- Added management review action owner workflow with overdue calculations and
  manager verification.
- Extended CI and DEV script targets for Mission 07 validation.
- Added Mission 07 architecture, security, testing, plan, and ADR
  documentation.

## 0.5.0 - 2026-08-15

- Added `pm_qms_kpi` with objectives, KPI definitions, historical KPI
  measurements, schedule/overdue logic, status calculation, and trend summaries.
- Added historical target, warning, and direction snapshots on KPI measurements
  so target changes do not rewrite past evaluations.
- Added customer performance and customer satisfaction models using Odoo
  `res.partner` for customer master data.
- Added supplier performance and supplier evaluation models using Odoo
  `res.partner` for supplier master data and transparent weighted scoring.
- Derived customer and supplier NCR counts from existing NCR source categories
  where structured source data exists.
- Extended control instance and process forms with performance relationships
  and summary counts.
- Updated CI and DEV script targets for Mission 06 validation.
- Added Mission 06 architecture, testing, security, plan, and ADR
  documentation.

## 0.4.0 - 2026-08-14

- Added `pm_qms_audit` with audit programs, audits, scope, criteria, planning,
  audit evidence, findings, controlled workflows, overdue indicators, and tests.
- Added auditor independence metadata with confirmation and documented override
  handling before an audit can move to ready.
- Added audit finding classifications for conformity, observation, opportunity
  for improvement, and internal nonconformity.
- Added controlled audit finding to NCR integration with source audit, source
  finding, audit evidence, and downstream NCR-to-CAPA continuity.
- Extended control instance and process views with audit/finding relationships
  and open finding metrics.
- Updated CI and DEV script targets for Mission 05 validation.
- Added Mission 05 architecture, security, testing, plan, and ADR documentation.

## 0.3.0 - 2026-08-14

- Added `pm_qms_risk` with risk/opportunity records, configurable scoring thresholds, workflow actions, overdue logic, attachments, and tests.
- Added `pm_qms_ncr` with nonconformity records, containment, investigation, verification, closure controls, relationships, and tests.
- Added `pm_qms_capa` with CAPA headers, 5 Why entries, multiple actions, effectiveness review, NCR/Risk source creation, and tests.
- Added `pm.qms.event` for lightweight operational workflow history across critical transitions.
- Hardened direct state changes for control instances and operational workflows.
- Added Mission 04 DEV script targets, CI workflow, addon validation, secret scan, and DEV backup/restore scripts.
- Added CI, backup/recovery, security, architecture, and ADR documentation for Mission 04.

## 0.2.0 - 2026-08-14

- Added `pm.qms.control.instance` to separate reusable Perfect Match framework controls from client implementation status.
- Added `pm_qms_documents` with controlled documents, document revisions, approval workflow, and attachment linkage.
- Added `pm_qms_evidence` with actual evidence records, evidence review workflow, and evidence completion counts.
- Added multi-company tests for control instances, documents, revisions, and evidence.
- Added security architecture documentation and ADRs for security, implementation separation, and document revisions.
- Added Mission 03 DEV script targets for install, update, and tests.

## 0.1.0 - 2026-08-14

- Added isolated Odoo 19 DEV Docker Compose stack with PostgreSQL 15 under `deployment/docker/dev/`.
- Added `deployment/scripts/odoo-dev.sh` for secrets, config validation, startup, install, and tests.
- Generated DEV runtime secrets outside Git under `/opt/perfect-match/secrets/odoo-dev/`.
- Scaffolded `pm_qms_core` as the first Odoo addon.
- Added QMS organization, process, proprietary control, implementation activity, evidence requirement, and external mapping models.
- Added QMS User, QMS Manager, and QMS Administrator groups with access rights and company-boundary record rules.
- Added sequence data, menus, native Odoo views, and post-install tests.
- Added DEV environment, architecture, testing documentation, and ADR-010.
- Validated `pm_qms_core` install and tests on Odoo 19.

## 0.0.1 - 2026-08-14

- Created engineering repository structure.
- Added agent instructions and planning framework.
- Added product, architecture, security, deployment, workflow, and IP policy documentation.
- Added initial ADRs.
- Added Plane project-management source files.
- Added initial 52-item engineering backlog.
- Added placeholder Odoo addon, standard pack, framework, deployment, and test directories.
