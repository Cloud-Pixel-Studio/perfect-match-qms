# ADR-022: Auditor Independence Model

Date: 2026-08-14

## Status

Accepted

## Context

Auditor objectivity matters, but simplistic technical rules such as "auditor
cannot belong to the same department" fail for small organizations or early
implementations where roles overlap.

## Decision

Record auditor independence as explicit audit metadata:

- independence required;
- independence confirmed;
- reviewed by;
- review date;
- notes.

An audit cannot move to Ready while independence is required and unconfirmed.
If independence is not required for a legitimate small-team reason, a documented
override note and reviewer are required.

## Consequences

The system supports objectivity review without inventing brittle organization
rules. The decision remains auditable and can be tightened later if a specific
standard pack or customer policy requires stricter criteria.
