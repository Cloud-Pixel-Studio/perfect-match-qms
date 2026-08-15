# Mission 07 Management Review

## Objective

Build the Perfect Match Digital QMS Management Review engine.

## Business Requirement

Management needs a controlled review record that preserves what was reviewed,
what was decided, and what actions remain open after the meeting.

## Technical Approach

- Add `pm_qms_management_review`.
- Store review headers on `pm.qms.management.review`.
- Store historical inputs on `pm.qms.management.review.input`.
- Store decisions on `pm.qms.management.review.decision`.
- Store follow-up actions on `pm.qms.management.review.action`.
- Generate snapshots from controlled Odoo ORM domains, not arbitrary SQL or
  user-defined Python.

## Components Affected

- `addons/pm_qms_management_review`
- `deployment/scripts/odoo-dev.sh`
- `.github/workflows/qms-ci.yml`
- Documentation and ADRs

## Database Changes

New Odoo models, sequences, ACLs, record rules, views, and demo records are
added by the addon. No direct PostgreSQL changes are made.

## Security Implications

Review, input, decision, and action models enforce company isolation. Snapshot
generation filters by company and organization. Completed review inputs are
locked from normal mutation.

## Dependencies

The addon depends on `pm_qms_audit` and `pm_qms_kpi`, which provide the
operational risk, NCR, CAPA, audit, and performance data sources needed for the
snapshot engine.

## Testing Strategy

Run:

```bash
./deployment/scripts/odoo-dev.sh test-mission07
```

Tests cover workflow, snapshot immutability, previous actions, customer and
supplier inputs, risk/NCR/CAPA inputs, management actions, and multi-company
security.

## Acceptance Criteria

- Mission 07 addon installs.
- Snapshot generation captures operational QMS data for the selected company,
  organization, and period.
- Completed reviews preserve historical inputs.
- Management review completion is separate from action closure.
- CI, manifest validation, secret scan, backup/restore, Odoo health, and Plane
  health pass.

## Rollback Considerations

Before production rollout, export or back up affected databases. In DEV, use
the existing backup and disposable restore scripts. The addon can be removed
from a DEV database only after preserving any required review history.
