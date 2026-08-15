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

## Run Tests

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh test-mission03
./deployment/scripts/odoo-dev.sh test-mission04
./deployment/scripts/odoo-dev.sh test-mission05
./deployment/scripts/odoo-dev.sh test-mission06
```

## Rules

- New Odoo models need tests for creation, security-sensitive relationships, constraints, and workflow behavior.
- Standard-pack tests must verify that seed/demo data contains Perfect Match proprietary wording only.
- Do not mark Plane work items done until a repeatable verification command exists.
- Do not copy external standard text into tests. Use generic examples such as `Example Standard` and `X.X`.
