# ADR-030: Management Decisions And Actions Architecture

Date: 2026-08-15

## Status

Accepted

## Context

Management Review produces both decisions and follow-up actions. The review
meeting may be complete while actions remain open.

## Decision

Use separate models:

- `pm.qms.management.review.decision` for decisions.
- `pm.qms.management.review.action` for follow-up work.

Actions have owners, target dates, priorities, status workflow, completion,
verification, and overdue calculations. Completing a review does not require
closing all review actions.

## Consequences

Management can close the meeting record while preserving open commitments.
Previous review actions can be captured as historical inputs in the next review
without duplicating the underlying action record.
