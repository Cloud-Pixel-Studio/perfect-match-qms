# Testing Strategy

Perfect Match Digital QMS uses Odoo-native tests for addon behavior.

## Current Scope

`pm_qms_core` includes post-install tests covering:

- Process creation and code persistence.
- Control creation, manual control codes, sequence generation, uniqueness, and lifecycle transitions.
- Activity relationships to a Perfect Match Control.
- Evidence requirement relationships and the `mandatory` flag.
- External mappings as reference-only records separate from proprietary control text.
- Basic QMS User read-only behavior and QMS Manager create behavior.
- Control instance separation from framework controls.
- Multi-company control instance isolation.

`pm_qms_documents` includes post-install tests covering:

- Controlled document creation.
- Revision creation and revision uniqueness.
- Submit, approve, activate, reject, and supersede workflow actions.
- Current revision updates and historical revision preservation.
- QMS User permission enforcement.
- Multi-company document and revision isolation.

`pm_qms_evidence` includes post-install tests covering:

- Evidence creation against a control instance and evidence requirement.
- Submit, review, accept, reject, and expire foundations.
- Rejected evidence review history.
- Required, accepted, and missing evidence counts.
- Requirement/control alignment.
- Organization/company document alignment.
- Multi-company evidence isolation.

Mission 04 adds tests covering:

- Risk and opportunity creation, sequence generation, scoring, residual
  scoring, workflow events, overdue logic, company isolation, organization
  constraints, unauthorized closure prevention, and protected attachment access.
- NCR creation, sequence generation, containment workflow, closure
  requirements, severity, relationships, company isolation, relationship
  constraints, and unauthorized closure prevention.
- CAPA creation, NCR-to-CAPA and risk-to-CAPA generation, 5 Why entries,
  multiple actions, overdue actions, implementation, effectiveness review,
  effective closure, ineffective reopening, company isolation, permissions, and
  the integration chain from control instance through evidence, NCR, CAPA,
  effectiveness review, and closure.

Mission 05 adds tests covering:

- Audit program creation, sequence generation, workflow history, and controlled
  program transitions.
- Audit creation, normalized scope, criteria, plan lines, team assignment,
  auditor independence confirmation, documented independence override, invalid
  transition blocking, completion requirements, overdue audit indicators, and
  event history.
- Audit evidence creation, document/control-instance alignment, and protected
  attachment access.
- Audit finding classifications: conformity, observation, opportunity for
  improvement, and internal nonconformity.
- Finding workflow, severity constraints, overdue finding and follow-up logic,
  and the rule that only internal nonconformity findings create NCRs.
- Audit finding to NCR source references, source audit evidence preservation,
  and downstream NCR-to-CAPA integration.
- The valid independent lifecycle state where Audit is completed while Finding
  remains action required, NCR remains open, and CAPA remains in progress.
- Multi-company isolation for audit programs, audits, scope, criteria, evidence,
  findings, and audit attachments.

Mission 06 adds tests covering:

- Objective creation, sequence generation, workflow actions, direct status write
  blocking, event history, KPI relationships, control instance relationships,
  process summary counts, and multi-company relationship constraints.
- KPI creation, target configuration validation, higher-is-better and
  lower-is-better evaluation, warning and off-target states, historical target
  snapshots, trend calculation, measurement schedule refresh, overdue logic,
  duplicate period blocking, and user measurement entry.
- Customer performance records using Odoo `res.partner`, customer satisfaction
  scoring and period validation, and NCR-derived customer complaint metrics.
- Supplier performance records using Odoo `res.partner`, supplier NCR-derived
  metrics, weighted supplier evaluation scoring, workflow completion events, and
  scoring validation.
- Multi-company isolation for objectives, KPIs, KPI measurements, customer
  performance, customer satisfaction, supplier performance, and supplier
  evaluations.
- Cross-module behavior from organization, process, control instance, objective,
  KPI, off-target measurement, and related risk without automatic NCR/CAPA
  creation.

Mission 07 adds tests covering:

- Management review creation, sequence generation, period validation,
  participant fields, workflow transitions, direct state write blocking, event
  history, and completion requirements.
- Snapshot generation for objectives, KPI measurements, customer performance,
  customer satisfaction, supplier performance, supplier evaluations, audit
  summaries, open findings, risks, opportunities, NCR, CAPA, and previous
  management review actions.
- Historical snapshot behavior proving that KPI target changes, newer KPI
  measurements, objective changes, audit finding closure, and CAPA closure do
  not rewrite captured review inputs.
- The valid state where Management Review is completed while Management Review
  Action remains open.
- Management Review Action owner workflow, overdue calculation, completion,
  manager verification, and permission boundaries.
- Multi-company isolation for reviews, inputs, decisions, and actions, plus
  snapshot generation that excludes other companies and other organizations.

Mission 08 adds tests covering:

- Framework pack creation, code/version/company uniqueness, workflow actions,
  and active pack definition locking.
- Project generator behavior across one or more active framework packs.
- Multi-pack control deduplication, source pack preservation, and required flag
  merging.
- Reuse of existing organization/control instances and rejection of duplicate
  control instances.
- Odoo project/task generation from reusable implementation activities.
- Task completion metrics using Odoo native task closure state.
- Evidence-driven readiness and separate activity completion metrics.
- Exclusion of not-applicable controls from the readiness denominator.
- Historical readiness assessments that remain unchanged after live
  implementation improves.
- Multi-company isolation for implementation projects, controls, readiness
  assessments, readiness items, and generated tasks.
- Project completion below full readiness requiring documented justification.

Mission 09 adds tests covering:

- Quality Management Pack seeding, activation, unique proprietary control
  codes, implementation activities, and mandatory evidence requirements.
- Content-quality checks proving seeded control content does not include
  external standard requirement text or certification outcome promises.
- Mapping profile metadata for standard name, edition, publisher, active state,
  incomplete starting coverage, pending mapping counts, and coverage percent.
- CSV mapping import validation, approval metadata, duplicate protection,
  missing-reference handling, and rejection of external requirement text
  columns.
- Mapping approval workflow, approved mapping lock behavior, and QMS
  Administrator-only profile-bound mapping creation.
- Mapping profile and pack multi-company isolation.
- Quality pack project generation, task creation, readiness, evidence
  readiness, not-applicable handling, shared-control deduplication, and
  historical readiness immutability.

Mission 10 adds tests covering:

- `pm_qms_migration` document import validation, scope checks, current revision
  creation, attachment handling, active document workflow, and migration notes.
- Evidence import validation, document linkage, attachment handling,
  under-review import state, and explicit rejection of direct `accepted` state.
- Manager-only import permissions.
- Mission 10 stack installation through the complete Quality Pack dependency
  chain.

## Run Tests

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh test-mission03
./deployment/scripts/odoo-dev.sh test-mission04
./deployment/scripts/odoo-dev.sh test-mission05
./deployment/scripts/odoo-dev.sh test-mission06
./deployment/scripts/odoo-dev.sh test-mission07
./deployment/scripts/odoo-dev.sh test-mission08
./deployment/scripts/odoo-dev.sh test-mission09
./deployment/scripts/odoo-dev.sh test-mission10
```

## Rules

- New Odoo models need tests for creation, security-sensitive relationships, constraints, and workflow behavior.
- Standard-pack tests must verify that seed/demo data contains Perfect Match proprietary wording only.
- Do not mark Plane work items done until a repeatable verification command exists.
- Do not copy external standard text into tests. Use generic examples such as `Example Standard` and `X.X`.
- External mapping tests may use metadata examples only. They must not use
  copied external requirement text as assertions or fixtures.
- Mission 10 customer-pilot tests and validation data must use
  `PILOT VALIDATION` labels unless authorized real customer data is supplied.
