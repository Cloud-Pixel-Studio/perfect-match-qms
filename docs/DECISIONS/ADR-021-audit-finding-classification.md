# ADR-021: Audit Finding Classification

Date: 2026-08-14

## Status

Accepted

## Context

Audit outputs are not always nonconformities. Treating every audit result as an
NCR would create unnecessary corrective-action records and distort audit
reporting.

## Decision

Use Perfect Match internal finding classifications:

- conformity;
- observation;
- opportunity for improvement;
- internal nonconformity.

Severity is available only for internal nonconformity findings and uses
Perfect Match or organization terminology: minor, major, critical. These values
are not certification-body classifications unless a future configured use case
explicitly defines that meaning.

Only internal nonconformity findings can create an NCR through the normal
workflow. Observations and opportunities for improvement can be accepted or
closed without creating NCRs.

## Consequences

Audit reports can show a balanced set of results without creating corrective
actions automatically. Formal NCR and CAPA records remain intentional and
traceable.
