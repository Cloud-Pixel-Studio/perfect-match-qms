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

## Run Tests

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh test-mission03
```

## Rules

- New Odoo models need tests for creation, security-sensitive relationships, constraints, and workflow behavior.
- Standard-pack tests must verify that seed/demo data contains Perfect Match proprietary wording only.
- Do not mark Plane work items done until a repeatable verification command exists.
- Do not copy external standard text into tests. Use generic examples such as `Example Standard` and `X.X`.
