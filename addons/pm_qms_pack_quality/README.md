# Perfect Match Quality Management Pack

`pm_qms_pack_quality` provides the first commercial Perfect Match quality
management pack.

It contains Perfect Match-authored quality controls, implementation activities,
mandatory evidence expectations, a versioned framework pack, and the generic
external-reference mapping workflow. It does not contain copied external
standard text and does not replace official publications.

## Architecture

```text
PERFECT MATCH METHODOLOGY
        |
        v
QMS CONTROL LIBRARY
        |
        v
QUALITY PACK v1.0
        |
        |-- Activities
        |-- Evidence Requirements
        `-- External Reference Mapping
                    |
                    v
              metadata only
```

The pack code is `PM-QMS-QUALITY`, version `1.0`.

The seeded library contains:

- 37 Perfect Match proprietary controls.
- 74 reusable implementation activities.
- 37 mandatory evidence requirements.
- Process domains for context, scope, leadership, risk, objectives, resources,
  competence, communication, document control, customer management, design,
  purchasing, operations, change, NCR, CAPA, audit, management review, and
  continual improvement.

Control codes use the `PM-QMP-*` prefix. That prefix identifies Perfect
Match-authored quality pack content and avoids confusing pack controls with
external standard references.

## External Reference Mapping

The addon provides the generic `pm.qms.mapping.profile` infrastructure and
extends `pm.qms.external.mapping`. Standard-specific profile records belong to
their standard addon. The current ISO 9001 profile is owned by
`pm_qms_iso9001`, not by this standard-neutral pack.

Mapping profiles start with no approved mappings unless approved metadata is
provided by the owning standard addon or imported by an authorized reviewer.

## CSV Import

The import wizard accepts UTF-8 CSV metadata with this header:

```csv
pm_control_code,standard_name,edition,reference,mapping_type,review_status,reviewed_by,review_date,notes
```

It validates all rows before creating mappings. Imported mappings must point to
controls inside the selected pack, match the selected profile's standard and
edition metadata, and use one of the controlled review states.

The import wizard rejects columns intended to carry external requirement text.
Only reference identifiers and Perfect Match-authored notes belong in this
system.

## Security

- QMS Users can read mapping profiles and mappings inside allowed companies.
- QMS Managers can read operational implementation records but cannot approve
  quality-pack mapping profiles.
- QMS Administrators control mapping profiles and profile-bound mappings.
- Approved mappings are locked against silent edits or deletion.
- Mapping records do not create, modify, or own operational evidence, tasks,
  readiness, NCR, CAPA, audit, KPI, or management review records.

## Tests

Run:

```bash
./deployment/scripts/odoo-dev.sh test-mission09
```

The test suite covers seeded pack structure, content-safety expectations,
mapping profile completeness, CSV import validation, approval workflow,
security boundaries, multi-company isolation, implementation project
generation, readiness behavior, shared-control deduplication, and historical
readiness immutability.
