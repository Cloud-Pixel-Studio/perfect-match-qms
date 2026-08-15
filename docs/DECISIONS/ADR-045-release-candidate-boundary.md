# ADR-045: Release Candidate Boundary

## Status

Accepted

## Context

The Oliva pilot validates the first commercial Quality Management Pack and the
implementation engine, but customer production data and approvals are not yet
available.

## Decision

Treat Mission 10 as `v1.0.0-rc1`, a technical release candidate.

The release candidate may claim:

- The full stack installs.
- The Quality Pack v1.0 generates 37 controls, 74 tasks, and 37 evidence
  requirements.
- Controlled workflows and historical snapshots work in the pilot database.
- Backup and restore tooling exists and is validated.

The release candidate must not claim:

- ISO certification or external standard compliance.
- Customer acceptance.
- Production go-live.
- Complete Oliva readiness.
- Approved external mapping coverage without a human-approved CSV.

## Consequences

Commercial readiness is framed honestly. The next milestone is customer
authorized onboarding and go-live preparation, not a retroactive claim that the
technical pilot is production certification evidence.
