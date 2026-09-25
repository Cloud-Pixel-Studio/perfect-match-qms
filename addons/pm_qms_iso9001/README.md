# Perfect Match QMS ISO 9001 Add-on

This add-on owns the ISO 9001 profile boundary for Perfect Match QMS. It
depends on the standard-neutral `pm_qms_pack_quality` methodology pack and
does not make the generic QMS foundation depend on ISO 9001.

## Versioned profiles

The add-on preserves the existing
`PM-QMS-QUALITY-ISO9001` / `2015` profile for ISO 9001:2015 and Amendment
1:2024. It also provides the separate
`PM-QMS-QUALITY-ISO9001-2026` / `2026` profile. The profiles coexist and
have no approved external mappings seeded automatically.

The 2026 profile uses edition metadata and PMQMS-authored workflow definitions
only. The licensed ISO publication remains the source for external
requirements; official requirement text is never copied into the product.

## Implementation and transition scenarios

The add-on seeds eight read-only scenario definitions for:

- new 2026 implementation;
- 2015-to-2026 transition;
- legacy or incomplete system migration;
- recertification;
- scope expansion;
- multi-site rollout;
- integrated management systems;
- partial implementation.

Scenario definitions describe entry conditions, expected outputs, migration
policy, and historical-record protection. They do not create client projects
or migrate client data automatically.

## Controlled gap assessments

QMS Managers and Administrators can start a company-scoped assessment from any
transition scenario. The assessment snapshots source and target editions,
initializes six Perfect Match-authored focus areas, requires owned remediation
for partial or gap results, and becomes immutable when completed. It neither
copies ISO requirement text nor infers certification.

## Initial implementation foundation

The add-on owns two selectable versions of the PM-QMS-ISO9001-INITIAL
implementation pack. Version 1.0 is the historical initial implementation
pack and remains active and unchanged. Version 1.1 is the Amendment 1:2024
aligned pack; both contain 13 phases and 37 generic control lines. The v1.1
pack reuses 30 activity definitions and adds seven focused revised definitions
for M25.11. It reuses the same 37 generic evidence definitions. Existing
implementation projects are not migrated automatically.

The existing mapping profiles remain a separate external-reference boundary
and continue to use the generic quality pack.
