# ADR-039: Proprietary Controls Vs External Reference Mapping

Date: 2026-08-15

## Status

Accepted

## Context

Perfect Match needs to show how its methodology relates to external standards,
but the system must not store copied external standard text or treat an
external clause as the internal control object.

## Decision

Perfect Match controls remain the authoritative implementation objects.
External mappings are metadata records that point from an external standard
name, edition, and reference identifier to a Perfect Match control.

The Quality Pack seeds proprietary controls using the `PM-QMP-*` prefix. The
external mapping profile stores standard name, edition, publisher, review
status, reviewer, review date, mapping type, and Perfect Match-authored notes
only.

## Consequences

The application can support traceability and review without embedding
copyrighted publication content. Clients still need authorized access to any
external standard they choose to use.
