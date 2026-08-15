# Perfect Match QMS Implementation

`pm_qms_implementation` provides the generic implementation engine for Perfect
Match Digital QMS.

It does not contain external standard text. Framework packs are versioned
Perfect Match deployment definitions that point to proprietary `pm.qms.control`
records.

## Main Flow

```text
FRAMEWORK
    |
    v
PACK
    |
    v
PROJECT GENERATOR
    |
    v
IMPLEMENTATION PROJECT
    |
    v
IMPLEMENTATION CONTROL
    |
    v
CONTROL INSTANCE
    |
    v
TASKS + EVIDENCE
    |
    v
READINESS
```

## Models

- `pm.qms.framework.pack`: versioned deployment pack.
- `pm.qms.framework.pack.control`: ordered pack-to-control relationship.
- `pm.qms.implementation.project`: client implementation generated from one
  or more active packs.
- `pm.qms.implementation.control`: deduplicated project control line linked to
  the shared operational control instance.
- `pm.qms.readiness.assessment`: historical readiness snapshot.
- `pm.qms.readiness.assessment.item`: immutable assessment line snapshot after
  completion.
- `pm.qms.project.generator.wizard`: transient generator wizard.
- `project.project` and `project.task`: native Odoo project/task integration.

## Pack Rules

Packs are company-scoped and uniquely identified by code, version, and company.
Only draft packs can change their control definition. Active or retired packs
must be replaced by a new version instead of edited in place.

The pack layer stores Perfect Match-authored deployment groupings only. It does
not store copied external requirement text.

## Generation And Sync

The generator requires at least one active pack. It creates or reuses an Odoo
project, resolves all active pack controls, deduplicates controls that appear in
multiple packs, and creates one implementation control line per unique control.

For each resolved control, the engine reuses the existing
`pm.qms.control.instance` for the selected organization and control. If one does
not exist, it creates it. This keeps operational documents, evidence, risks,
NCRs, CAPAs, audits, KPIs, reviews, and readiness aligned to the same client
implementation record.

Synchronization is additive and preservation-oriented. It creates missing
implementation controls and missing generated tasks, updates source pack links,
and does not delete operational history.

## Odoo Tasks

Reusable `pm.qms.activity` records generate native `project.task` records.
Generated tasks keep links to the implementation project, implementation
control, control instance, and reusable activity.

Activity completion is based on Odoo's native task state mechanism through
`project.task.is_closed`. The implementation engine does not infer completion
from translated stage names.

## Readiness

Readiness is an internal implementation metric:

```text
ready applicable controls / total applicable controls * 100
```

Controls marked not applicable are excluded from the denominator. Evidence
completion and activity completion are calculated separately.

Readiness does not mean external approval or a predicted audit outcome. It only
reflects the current Perfect Match implementation state captured by the
application.

## Security

The addon uses existing QMS groups:

- QMS Users can read implementation records inside allowed companies.
- QMS Managers can generate projects, synchronize frameworks, run readiness
  assessments, and manage implementation execution.
- QMS Administrators can configure framework packs.

All persistent models have company record rules. Managers inherit the Odoo
Project Administrator group so the generator can create native projects and
tasks through Odoo access controls.

## Tests

Run:

```bash
./deployment/scripts/odoo-dev.sh test-mission08
```

The test suite covers pack version locking, multi-pack deduplication, control
instance reuse, generated task metrics, evidence and activity readiness,
not-applicable denominator handling, historical readiness immutability,
multi-company security, and completion justification.
