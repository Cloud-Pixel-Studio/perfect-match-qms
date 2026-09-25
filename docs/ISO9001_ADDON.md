# ISO 9001 Add-on

The technical add-on is `pm_qms_iso9001`. It depends on
`pm_qms_pack_quality`, which supplies the proprietary PM-QMS-QUALITY
methodology pack. The generic QMS foundation does not depend on ISO 9001.

## Versioned profile boundary

The add-on preserves the active ISO 9001:2015 + Amendment 1:2024 profile
(`PM-QMS-QUALITY-ISO9001`) and adds a separate ISO 9001:2026 profile
(`PM-QMS-QUALITY-ISO9001-2026`). They coexist; the 2026 profile does not
rewrite or retire 2015 records.

Profiles contain edition metadata and reviewed external reference records only.
The product never stores copied ISO publication text or presents unapproved
interpretation as a requirement.

## Implementation and transition scenarios

The add-on provides read-only, company-scoped scenario definitions for:

- new ISO 9001:2026 implementation;
- transition from ISO 9001:2015;
- legacy or incomplete-system migration;
- recertification;
- scope expansion;
- multi-site rollout;
- integrated management systems;
- partial implementation.

The scenarios are workflow entry guidance. They do not create customer data,
migrate records, mark controls conforming, or claim certification automatically.

## Customer navigation

Users see **Perfect Match QMS > Standards > ISO 9001 > Profiles** and
**Implementation and Transition Scenarios**. The views report profile and
scenario metadata, coverage counts, and reviewed reference identifiers. They
never display copied standard requirements or unapproved guidance.

The licensed ISO 9001:2026 publication and competent QMS review remain required
before approving detailed external mappings or customer transition decisions.

The add-on deliberately does not implement ISO 14001, ISO 45001, AS9100,
AS9120, IATF 16949, standard-specific billing, or a cross-standard comparison
dashboard. Future standards belong in separate add-ons.
