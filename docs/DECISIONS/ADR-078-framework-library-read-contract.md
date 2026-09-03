# ADR-078: Technical Framework Library Read Contract

## Status

Accepted for M30.4 implementation.

## Context

The first customer Quality Manager must be able to consume the same-company
technical framework library while the implementation generator materializes
customer-owned operational processes and control instances. Mission 19 scope
rules previously treated framework source records as if they were operational
customer records, so a clean customer could not read the controls required by
the generator.

## Decision

Allow same-company QMS users to read framework organizations, processes, and
controls when the source organization is explicitly marked `framework`. Keep
the existing operational organization/process scope as the separate path for
customer records. Framework source records remain read-only to normal customer
users, and company record rules continue to apply.

Split organization and process read rules from their operational mutation
rules so granting technical read access cannot grant framework write or delete
access. Framework pack, pack-control, area, and activity reads remain bounded
by their existing same-company rules. The generator continues to create only
derived processes, control instances, implementation controls, and tasks under
the selected customer organization.

## Consequences

- Technical framework read is not operational customer scope membership.
- Framework organizations and processes are not added to
  `qms_organization_ids` or `qms_effective_process_ids`.
- Cross-company framework data remains inaccessible.
- Normal Quality Managers cannot create, write, or delete framework sources.
- Generator and repeated framework synchronization preserve the M30.1
  single-derived-process and zero-growth behavior.
- Framework source content is still subject to the existing authoring/admin
  workflow; this ADR does not add a new authoring role or bypass.

## Verification

The M30.4 security regression covers same-company framework dependencies,
cross-company isolation, mutation denial, customer operational isolation, and
first-customer generation followed by repeated synchronization.
