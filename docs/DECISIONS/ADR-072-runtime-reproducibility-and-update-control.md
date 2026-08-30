# ADR-072: Runtime Reproducibility and Update Control

## Status

Accepted for implementation in deployment tooling.

## Decision

Persistent Odoo and PostgreSQL images used by Perfect Match QMS are selected
from the tracked `deployment/runtime/runtime-lock.json` file and referenced by
tag plus immutable digest. Alpine utility operations use the same explicit
lock boundary. Customer Compose files use `pull_policy: never`; normal
operation verifies local image identity and fails closed when an approved image
is missing.

Runtime acquisition is an intentional operator action through
`runtime-fetch`. Upgrade preflight compares the current and target release
locks and requires explicit acknowledgement only when the approved runtime
actually changes. Deployment and bundle manifests record the lock identity.

## Consequences

- Reboots, restarts, cache loss, and ordinary health checks cannot select a new
  upstream runtime.
- Offline verification works from local Docker metadata without contacting a
  registry.
- Operators must explicitly prepare exact images before starting an instance.
- A runtime digest change is part of a tested Perfect Match release event.
- `restart: unless-stopped` remains available for resilience; it restarts an
  existing container and does not update its image.

## Scope

This decision governs Perfect Match QMS Odoo/PostgreSQL application runtimes.
Host operating-system security updates and unrelated Plane service images are
outside this lock. No QMS model, ISO content, licensing semantics, or customer
data is changed by the runtime controls.
