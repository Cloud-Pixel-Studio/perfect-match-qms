# ADR-010: Perfect Match Control Model

Date: 2026-08-14

## Status

Accepted

## Context

Perfect Match Digital QMS must support multiple standards and customer
implementations while protecting third-party intellectual property. The product
needs a reusable internal control object that expresses Perfect Match
methodology in original language. External standards still need traceability,
but they must not become the source data model.

## Decision

Perfect Match Controls are proprietary reusable implementation objects stored in
`pm.qms.control`.

External standard relationships are stored separately in
`pm.qms.external.mapping` using reference metadata only:

- standard name;
- edition;
- reference identifier;
- Perfect Match internal note.

No external standard requirement text is stored in the core model, seed data,
tests, or UI.

## Alternatives Considered

- Model controls directly as ISO or other standard clauses. Rejected because it
  couples the product to one framework and creates IP risk.
- Store standard text beside controls for convenience. Rejected because it
  encourages copyrighted content leakage and makes multi-standard reuse harder.
- Delay mappings entirely. Rejected because traceability is a foundational need
  for future standard packs and pilots.

## Consequences

- Perfect Match can build proprietary reusable methods once and map them to many
  external frameworks later.
- Standard packs can add mappings without redefining the core object.
- Tests and reviews must continue checking that mappings are reference-only.
- Users may need access to licensed standards outside the application when they
  need authoritative external requirement language.

## Future Benefits

This structure supports ISO 9001, IATF, AS, CMMC, and other future packs without
duplicating equivalent implementation controls across packs.
