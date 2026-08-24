# Standard Add-on Architecture

Perfect Match QMS uses one management-system standard per add-on. The
architecture has three layers:

| Layer | Ownership | Standard dependency |
| --- | --- | --- |
| Generic foundation | `pm_qms_core`, operational addons, generic shell | None |
| Proprietary methodology | `pm_qms_pack_quality`, implementation and readiness engines | None |
| Standard profile | One add-on such as `pm_qms_iso9001` | Depends on the methodology it profiles |

Generic controls, activities, evidence requirements, framework packs, mapping
records, implementation generation, readiness, action aggregation, and
analytics remain standard-neutral. A standard add-on may provide profile
metadata, reference identifiers, review workflows, and customer navigation.

## ISO 9001 boundary

`pm_qms_iso9001` is the only standard add-on in this release. It owns the
ISO 9001 edition profile and its read-only customer view. Its post-init hook
adopts the existing stable profile record instead of duplicating it. The
current Demo has zero approved mappings by design.

## Framework administration

Reusable framework definitions are administered from **Configuration >
Framework Administration** by `QMS Administrator`. Quality Managers and
other customer roles use the generated implementation records and operational
menus; they do not rewrite the reusable framework catalog.

## Intellectual property

Only standard name, edition, publisher, reference identifiers, review status,
and original Perfect Match notes are stored. The repository and UI contain no
copied ISO text. A future standard gets a separate add-on, tests, deployment
selection, documentation, and entitlement decision.

See [ADR-062](DECISIONS/ADR-062-mission23-standard-addon-architecture.md) for
the recorded decision.
