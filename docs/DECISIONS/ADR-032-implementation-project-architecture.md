# ADR-032: Implementation Project Architecture

Date: 2026-08-15

## Status

Accepted

## Context

Client implementations need a controlled project header, generated control
scope, generated tasks, metrics, workflow status, and a link to native Odoo
project execution.

## Decision

Create `pm.qms.implementation.project` as the client implementation header. It
belongs to one company and organization, references one or more active
framework packs, and can create an Odoo `project.project`.

Generated implementation controls live on `pm.qms.implementation.control`.
They point to reusable controls and operational control instances. Generated
Odoo tasks point back to the implementation project, implementation control,
control instance, and reusable activity.

## Consequences

The implementation project becomes the orchestration layer while operational
evidence and status remain on `pm.qms.control.instance`. This keeps the
framework reusable and avoids copying client state into control definitions.
