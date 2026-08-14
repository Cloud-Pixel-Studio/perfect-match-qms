# ADR-012: Framework Definition vs Client Implementation

Date: 2026-08-14

## Status

Accepted

## Context

Perfect Match controls are reusable framework methodology. A client
implementation needs its own status, owner, target dates, documents, and
evidence without changing the reusable control definition.

## Decision

Keep `pm.qms.control` and `pm.qms.control.instance` separate.

`pm.qms.control` defines the reusable Perfect Match expectation.

`pm.qms.control.instance` represents one organization's implementation of that
control.

Documents and actual evidence attach to the control instance.

## Benefits

- Multiple organizations can implement the same control independently.
- Implementation status does not pollute framework lifecycle state.
- Future project generation can create client work from reusable controls.
- Evidence tracking remains organization-specific.
- Standard mappings can stay reference-only on the framework side.
- Multi-client isolation can be tested at the implementation layer.

## Alternatives Considered

- Put implementation status directly on `pm.qms.control`. Rejected because it
  makes reusable framework controls client-specific.
- Create client copies of every control without a link to the framework.
  Rejected because it weakens reuse, mapping, and future update flows.

## Consequences

Future dashboards must speak in implementation terms such as Evidence Completion
and Implementation Status. They must not claim certification readiness.
