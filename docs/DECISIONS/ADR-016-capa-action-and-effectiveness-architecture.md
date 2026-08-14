# ADR-016: CAPA Action and Effectiveness Architecture

Date: 2026-08-14

## Status

Accepted

## Context

CAPA often requires multiple actions and is not complete merely because actions
were implemented. Effectiveness review needs to preserve both effective and
ineffective outcomes.

## Decision

Use `pm.qms.capa` as the CAPA header and `pm.qms.capa.action` for individual
actions. Use `pm.qms.capa.why` for structured 5 Why entries.

CAPA state separates implementation from effectiveness review. Ineffective
results are retained and can be reopened for additional actions without
clearing the prior effectiveness result.

## Consequences

CAPA can model several owners and target dates without overloading the header.
Effectiveness becomes a first-class workflow decision and is testable.
