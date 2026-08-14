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

## Run Tests

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh test-mission03
./deployment/scripts/odoo-dev.sh test-mission04
```

## Rules

- New Odoo models need tests for creation, security-sensitive relationships, constraints, and workflow behavior.
- Standard-pack tests must verify that seed/demo data contains Perfect Match proprietary wording only.
- Do not mark Plane work items done until a repeatable verification command exists.
- Do not copy external standard text into tests. Use generic examples such as `Example Standard` and `X.X`.
