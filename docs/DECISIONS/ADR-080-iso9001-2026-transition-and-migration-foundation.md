# ADR-080: ISO 9001:2026 transition and implementation foundation

- Status: Proposed
- Date: 2026-09-25
- Scope: ISO 9001 standard add-on, implementation engine, migration workflows
- Owner: Product Owner

## Decision

Perfect Match QMS will support ISO 9001:2026 as a versioned standard profile while
preserving ISO 9001:2015 and all historical client implementation records.

The product will not copy the ISO publication text. It will store Perfect Match
controls, activities, evidence expectations, and reviewed reference metadata.
Reference identifiers and mappings require an authorized human review before
they become active.

## Why

ISO 9001:2026 is the current published edition. The official ISO summary describes
targeted updates focused on clarity, quality culture and leadership, separation
of risks and opportunities, and improved alignment with other management-system
standards. These themes guide product discovery, but they are not a substitute
for the licensed standard text or certification-body transition instructions.

## Supported onboarding scenarios

The implementation engine must distinguish at least:

- `NEW_IMPLEMENTATION_2026`: no existing QMS;
- `TRANSITION_2015_TO_2026`: active or certified 2015 system;
- `LEGACY_STANDARD_TRANSITION`: older ISO 9001 edition;
- `IMPLEMENTED_NOT_CERTIFIED`: operational QMS without certification;
- `MIGRATION_FROM_OTHER_SYSTEM`: spreadsheets, SharePoint, ERP, or another QMS;
- `RECERTIFICATION`: existing certified system approaching a certification event;
- `SCOPE_EXPANSION`: new products, processes, sites, or organizations;
- `MULTI_SITE_ROLLOUT`: phased deployment across sites;
- `INTEGRATED_MANAGEMENT_SYSTEM`: ISO 9001 combined with another framework;
- `PARTIAL_IMPLEMENTATION`: selected QMS capabilities only.

The scenario is implementation metadata. It must not be interpreted as a
certification decision.

## Versioning and historical integrity

- Standard profiles are immutable once approved.
- A client implementation references exactly one active target profile.
- Historical controls, evidence, audits, CAPA, KPI measurements, and management
  reviews retain their original profile/version context.
- A transition creates a new assessment and implementation scope; it does not
  rewrite completed historical records.
- Migration operations require an auditable source, mapping decision, actor,
  timestamp, and validation result.
- Rollback restores the implementation workspace and imported records without
  deleting the source history.

## Product boundaries

The generic QMS foundation remains independent of ISO 9001. The ISO add-on owns
standard profile metadata and reviewed mappings. The implementation engine owns
projects, controls, activities, evidence, and readiness. Client operational
records remain separate from reusable framework definitions.

No customer license, user entitlement, Demo2 data, or existing ISO 9001:2015
profile is changed by this ADR.

## Acceptance gates

Before enabling ISO 9001:2026 for customer use:

1. The licensed publication and certification-body transition guidance are
   available to the Product Owner.
2. An approved 2015-to-2026 mapping has been reviewed by a competent QMS
   practitioner.
3. New profile records pass duplicate, immutability, company-scope, and
   historical-integrity tests.
4. A migration dry run succeeds on an isolated copy.
5. Reversal and backup restoration are verified.
6. Documentation states that PMQMS implementation readiness is not certification.
7. QMS, security, migration, and authorization tests pass.

## Consequences

This preserves existing customers and allows new 2026 implementations without
a destructive upgrade. It requires version-aware records and a formal
migration workflow before the 2026 profile is activated.

## Explicit non-goals

- No copied ISO requirement text.
- No automatic certification claim.
- No destructive conversion of 2015 data.
- No automatic reassignment of evidence without review.
- No changes to the delivered Demo2 environment.
