# ADR-035: Readiness Calculation Strategy

Date: 2026-08-15

## Status

Accepted

## Context

Perfect Match needs a simple implementation readiness signal that separates
control readiness from evidence completion and activity completion.

## Decision

Calculate project readiness as:

```text
ready applicable controls / total applicable controls * 100
```

Controls marked not applicable are excluded from the denominator. A control is
ready only when the operational control instance is implemented, mandatory
evidence requirements have accepted evidence, and required generated tasks are
closed.

Evidence completion and activity completion are calculated separately.

## Consequences

Readiness is transparent and explainable. It is not an external approval claim
or a predicted audit outcome. It is an internal Perfect Match implementation
metric.
