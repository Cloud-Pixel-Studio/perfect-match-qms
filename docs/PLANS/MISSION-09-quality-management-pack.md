# Mission 09 Quality Management Pack

## Objective

Build the first commercial Perfect Match quality management pack on top of the
generic implementation engine delivered in Mission 08.

## Business Requirement

Perfect Match needs a deployable quality-management pack that can generate real
client implementation projects, tasks, evidence expectations, and readiness
records without storing copied external standard text. External standard
alignment must be traceable through metadata only and must require human review
before it is treated as approved.

## Technical Approach

- Add `pm_qms_pack_quality`.
- Seed a proprietary Quality Management Pack `PM-QMS-QUALITY` version `1.0`.
- Seed 37 Perfect Match-authored controls with implementation activities and
  mandatory evidence expectations.
- Add mapping profile workflow for external reference metadata.
- Extend external mappings with mapping type, review status, reviewer, review
  date, and import batch metadata.
- Add a CSV import wizard that validates all rows before creating mappings.
- Keep the official-standard mapping profile active but incomplete until a
  human-approved CSV is supplied.
- Add a content-safety scan to reduce the risk of accidentally committing
  licensed external publications or copied standard text.
- Extend Mission 08 project generation so controls from framework-owned
  processes create client organization process records when needed.

## Components Affected

- `addons/pm_qms_pack_quality`
- `addons/pm_qms_implementation`
- `deployment/scripts/odoo-dev.sh`
- `deployment/scripts/qms-content-safety.py`
- `.github/workflows/qms-ci.yml`
- `framework/mappings/iso9001-approved-mapping.csv.example`
- Documentation and ADRs

## Database Changes

The addon adds Odoo models, ACLs, record rules, views, and a transient import
wizard. It also extends `pm.qms.control` and `pm.qms.external.mapping` through
normal Odoo addon inheritance.

Seed data is created through the Odoo ORM in the module post-init hook. No
direct PostgreSQL writes are used.

## Security Implications

Mapping profiles and profile-bound mappings are company-isolated.
Profile-bound mapping creation and approval require QMS Administrator
authority. Approved mappings cannot be silently changed or deleted.

External mapping metadata is intentionally separate from operational execution
records. Mapping changes do not create evidence, close tasks, mark controls
ready, or change readiness history.

## Dependencies

`pm_qms_pack_quality` depends only on:

- `pm_qms_core`
- `pm_qms_implementation`

Earlier operational addons remain part of the Mission 09 validation stack
because the commercial pack must work with the complete current QMS runtime.

## Testing Strategy

Run:

```bash
./deployment/scripts/odoo-dev.sh test-mission09
```

Tests cover pack seed content, mapping profile completeness, CSV import
validation, approval locking, security, multi-company isolation, generator
compatibility, shared-control deduplication, readiness, and immutable
historical readiness assessments.

## Acceptance Criteria

- `pm_qms_pack_quality` installs on Odoo 19.
- Mission 02 through Mission 09 Odoo test stack passes.
- Quality Pack version `1.0` is active.
- Pack controls are proprietary Perfect Match controls, not external
  requirement records.
- Every seeded control has implementation activities and at least one mandatory
  evidence expectation.
- External mapping profile stores metadata only and starts incomplete.
- Mapping imports reject external requirement text columns.
- Human approval is required before mappings count as approved coverage.
- Project generation creates client implementation records, Odoo tasks, and
  readiness data from the quality pack.
- CI, manifest validation, secret scan, content-safety scan, backup/restore,
  Odoo health, and Plane health pass.

## Rollback Considerations

Use the DEV backup and restore scripts before broader rollout. Framework pack
content is versioned, so methodology changes should happen through a new pack
version or new mapping profile rather than editing active records in place.
