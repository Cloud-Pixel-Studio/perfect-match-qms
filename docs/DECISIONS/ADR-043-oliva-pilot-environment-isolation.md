# ADR-043: Oliva Pilot Environment Isolation

## Status

Accepted

## Context

Mission 10 needs a customer-specific technical pilot for Oliva Torras without
mixing pilot state into DEV or Plane infrastructure.

## Decision

Create a dedicated Odoo pilot stack for Oliva with:

- Dedicated PostgreSQL database: `pmqms_oliva_pilot`.
- Dedicated Docker network: `pmqms_oliva_pilot_network`.
- Dedicated PostgreSQL and Odoo filestore volumes.
- Secrets stored outside Git under `/opt/perfect-match/secrets/odoo-oliva-pilot`.
- Odoo ports bound to `127.0.0.1` on the VM.

No public reverse-proxy route is created by default.

## Consequences

The pilot can be installed, validated, backed up, restored, and discarded
without mutating DEV or Plane. Customer access requires a separate controlled
DNS/TLS/reverse-proxy change.
