# ISO 9001:2026 transition architecture

## Purpose

This document defines the product foundation for new ISO 9001:2026
implementations, 2015-to-2026 transitions, and controlled migrations from
other QMS sources.

It is an architecture document, not a reproduction of the ISO publication.

## Version-aware model

```text
Standard family
    |
    +-- Standard profile: ISO 9001 / 2015
    |
    +-- Standard profile: ISO 9001 / 2026
    |
    +-- Future profiles
             |
             v
Reviewed external mappings
             |
             v
Perfect Match framework controls
             |
             v
Customer implementation controls
             |
             +-- documents
             +-- evidence
             +-- tasks
             +-- risks and opportunities
             +-- audits
             +-- CAPA
             +-- KPI
             +-- management review
```

A standard profile is reference metadata. A Perfect Match control is proprietary
implementation content. A customer control instance is operational client
state. These layers must not be merged.

## Required information

Every target implementation must record:

- standard family and edition;
- scenario type;
- implementation status;
- certification status, if supplied by the customer;
- target scope;
- companies and sites;
- source system;
- migration baseline;
- responsible owner;
- transition target date;
- certification-body coordination status;
- approval state.

## Assessment states

The transition workflow uses explicit states:

```text
Draft
  -> Assessed
  -> Gap Analysis
  -> Migration Planned
  -> In Implementation
  -> Internal Review
  -> Management Approved
  -> Ready for Certification Review
  -> Closed
```

A state called `Ready for Certification Review` is not a certification result.

## Migration principles

- Preserve source records as historical data.
- Create target records through controlled mappings.
- Never silently overwrite accepted evidence or completed reviews.
- Detect duplicates before import.
- Validate companies, sites, processes, owners, attachments, and relationships.
- Require human confirmation for ambiguous mappings.
- Produce an import report with created, reused, skipped, rejected, and manually
  reviewed records.
- Keep a reversible migration package and backup.

## New implementation versus transition

### New implementation

The generator starts with a blank client scope, selects the 2026 profile,
creates the approved Perfect Match implementation pack, and produces initial
controls, activities, evidence expectations, and readiness tasks.

### 2015 transition

The system creates a transition workspace. Existing 2015 records remain
unchanged. The workspace compares reviewed mappings, identifies affected
controls, requests updated evidence where needed, and creates transition tasks.

### Other migrations

The migration layer first inventories the source. It then maps source
documents, processes, evidence, risks, audits, and actions into PMQMS models.
Unmapped or ambiguous records remain in an exception queue rather than being
discarded.

## Security and authorization

- Framework profiles and approved mappings are administrative master data.
- Customer implementation records remain company/site scoped.
- Normal QMS users cannot edit approved framework definitions.
- Migration execution requires an authorized implementation role.
- Approval of a migration package is separate from technical import.
- All state changes are auditable.

## Controlled migration package boundary

An approved readiness review may produce one versioned migration package. The
package captures scope, source inventory, compatibility notes, isolated dry-run
planning, backup identity and digest, rollback controls, and an independent
approval. Its deterministic manifest detects changes between preflight,
submission, and approval.

The package has no execution method. It cannot import records, alter a customer
database, deploy code, replace a framework pack, rewrite history, or update an
environment. Technical execution and execution reporting remain a separate
future increment with their own authorization and rollback gates.

## Demo and release isolation

The delivered Demo2 remains unchanged. ISO 9001:2026 work is validated in a
separate development or laboratory instance. The 2015 Demo profile remains
available for historical demonstrations until a dedicated 2026 scenario passes
its own validation.

## 2026 pack review and release gates

A separate original ISO 9001:2026 implementation-pack draft is maintained in
`docs/ISO9001_2026_IMPLEMENTATION_PACK.md` and
`addons/pm_qms_iso9001/content/iso9001_2026_implementation_pack_v1_draft.json`.
It does not replace the 2015/2024 pack or rewrite existing implementation
history.

The draft remains unavailable for customer implementation until all of the
following are complete:

- an authorized reviewer verifies detailed traceability against the licensed
  ISO 9001:2026 publication, including paragraph-level applicability;
- licensed ISO 9000 vocabulary is consulted where needed;
- applicable certification-body transition requirements are confirmed;
- a competent QMS practitioner records approval of coverage, control sufficiency,
  applicability, evidence examples, and acceptance criteria;
- product tests and release gates pass on a new, versioned revision.

The profile and pack remain separate metadata/content layers. The draft pack and
mapping profile stay in draft state; mappings remain unapproved, evidence
examples are non-mandatory, and activation is blocked in code. The reference
inventory is a coverage aid, not a conformity or certification claim.
