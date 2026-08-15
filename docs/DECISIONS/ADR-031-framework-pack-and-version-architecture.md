# ADR-031: Framework Pack And Version Architecture

Date: 2026-08-15

## Status

Accepted

## Context

Perfect Match needs reusable deployment packages that can group proprietary
controls for client implementations. Pack definitions must be stable once used
so prior implementation projects can still be understood later.

## Decision

Create `pm.qms.framework.pack` and `pm.qms.framework.pack.control`.

Packs are company-scoped and uniquely identified by code, version, and company.
Pack controls are ordered and can mark whether a control is required. Only
draft pack definitions can change. Active or retired packs require a new
version instead of direct mutation.

Packs store Perfect Match-authored grouping and applicability metadata. They do
not store copied external standard text.

## Consequences

Implementation projects can reference a known pack version. Later methodology
changes happen through a new pack version instead of rewriting history.
