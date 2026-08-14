# ADR-014: Risk and Opportunity Architecture

Date: 2026-08-14

## Status

Accepted

## Context

Perfect Match Digital QMS needs operational risk and opportunity tracking
before standard packs or dashboards expand. The model must support process,
control instance, document, owner, scoring, response, review, and closure data
without storing external standard text.

## Decision

Use one `pm.qms.risk` model for both risks and opportunities, distinguished by
`risk_type`.

Scoring uses the Perfect Match method of likelihood times impact with
configurable threshold parameters. The initial default uses 1-5 likelihood and
1-5 impact.

Risks and opportunities relate to `pm.qms.control.instance` and documents, not
to reusable framework controls as mutable operational state.

## Consequences

One model avoids duplicate workflows and makes opportunity management available
without a separate app. Future configuration screens can expose threshold
parameters without migrating core risk records.
