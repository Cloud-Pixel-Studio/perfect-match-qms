# ADR-019: Internal Audit Architecture

Date: 2026-08-14

## Status

Accepted

## Context

Perfect Match Digital QMS needs reusable internal audit capability before
standard packs are implemented. The audit foundation must support future ISO,
IATF, environmental, safety, aerospace, supplier, and CMMC use cases without
copying external standard text or turning reusable framework controls into
client operational state.

## Decision

Create `pm_qms_audit` as a client operational addon.

Use separate models for:

- audit programs;
- audits;
- audit scope;
- audit criteria;
- audit plan lines;
- audit evidence;
- audit findings.

Audits and findings relate to `pm.qms.control.instance` and `pm.qms.process`.
They do not add operational audit state to `pm.qms.control`.

Audit completion is separate from finding, NCR, and CAPA closure. A completed
audit report may still have action-required findings, open NCRs, and CAPAs in
progress.

## Consequences

The audit foundation can support future standard-specific packs and supplier or
customer audit variants without changing the core QMS control model. Users get
operational traceability while corrective action remains governed by existing
NCR and CAPA workflows.
