# Mission 08 Project Generator And Readiness

## Objective

Build the generic Perfect Match Digital QMS implementation engine used to
deploy future framework packs.

## Business Requirement

Perfect Match needs a reusable deployment layer that can generate client
implementation projects from versioned framework packs, assign operational work
through Odoo projects/tasks, reuse existing client control instances, and show
current and historical readiness without copying external standard text.

## Technical Approach

- Add `pm_qms_implementation`.
- Add versioned framework packs and pack-control relationships.
- Add implementation projects generated from one or more active packs.
- Deduplicate shared controls across packs.
- Reuse one organization/control `pm.qms.control.instance` instead of creating
  duplicate implementation records.
- Generate native Odoo project tasks from reusable `pm.qms.activity` records.
- Calculate readiness from control implementation status, mandatory evidence,
  and generated task completion.
- Store historical readiness assessments as immutable snapshots after
  completion.

## Components Affected

- `addons/pm_qms_implementation`
- `deployment/scripts/odoo-dev.sh`
- `.github/workflows/qms-ci.yml`
- Documentation and ADRs

## Database Changes

The addon adds Odoo models, sequences, ACLs, record rules, views, a wizard, and
demo records. It extends `project.project`, `project.task`, and
`pm.qms.control.instance` through normal Odoo addon inheritance. No direct
PostgreSQL schema manipulation is performed outside the Odoo ORM.

## Security Implications

Implementation packs, projects, controls, readiness assessments, and readiness
items are company-isolated. Project generation requires QMS Manager authority.
Pack configuration requires QMS Administrator authority. QMS Managers inherit
Odoo project management permissions so generated projects and tasks are created
through supported Odoo security paths.

## Dependencies

`pm_qms_implementation` depends only on:

- `pm_qms_core`
- `pm_qms_evidence`
- `project`

Earlier operational modules remain part of the Mission 08 validation stack
because they depend on the same shared control instance architecture.

## Testing Strategy

Run:

```bash
./deployment/scripts/odoo-dev.sh test-mission08
```

Tests cover versioned pack behavior, deduplication, control-instance reuse,
task generation, task completion, evidence readiness, not-applicable controls,
historical readiness snapshots, multi-company security, and controlled project
completion.

## Acceptance Criteria

- `pm_qms_implementation` installs on Odoo 19.
- Mission 02 through Mission 08 Odoo test stack passes.
- Framework packs are versioned and protected after activation.
- Multi-pack generation creates one implementation control per unique control.
- Existing organization/control instances are reused.
- Generated task completion uses Odoo native task state closure.
- Readiness excludes not-applicable controls from the denominator.
- Completed readiness assessments are immutable historical snapshots.
- CI, manifest validation, secret scan, backup/restore, Odoo health, and Plane
  health pass.

## Rollback Considerations

Use the DEV backup and restore scripts before wider rollout. Generated
implementation records are operational history, so removal should happen only
after preserving any required project, task, control-instance, evidence, and
readiness records.
