# Testing Strategy

Perfect Match Digital QMS uses Odoo-native tests for addon behavior.

## Current Scope

`pm_qms_core` includes post-install tests covering:

- Control sequence generation.
- Basic control lifecycle transitions.
- Separate external mapping records.
- Activity and evidence requirement relationships.
- The absence of any `standard_text` field that could encourage copying external standard content.

## Run Tests

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh test-core
```

## Rules

- New Odoo models need tests for creation, security-sensitive relationships, constraints, and workflow behavior.
- Standard-pack tests must verify that seed/demo data contains Perfect Match proprietary wording only.
- Do not mark Plane work items done until a repeatable verification command exists.
