# ADR-076: M29.2 Recurring Backup and RPO Scheduler

## Status

Accepted for repository implementation; production deployment not executed.

## Context

M29.1 established encrypted, manifest-verified customer recovery points,
off-host transfer, and failure-safe retention. M29.2 needs a predictable
per-instance schedule without claiming that repository tests are a live
production schedule.

## Decision

Use templated systemd services and timers per customer instance. Intraday
backup runs at fixed UTC slots 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00
with `Persistent=true` and `RandomizedDelaySec=30min`. Daily runs at 00:45 UTC
and monthly runs at 01:30 UTC on the first calendar day. The designed maximum
interval is 4.5 hours, below the six-hour RPO target. Each run uses a shared
per-instance nonblocking lock and an explicit timeout.

The scheduler delegates backup, verification, transfer, and retention to the
M29.1 interfaces. Retention runs only after backup and off-host verification
succeed. Failure returns nonzero, writes atomic sanitized status, preserves the
previous successful recovery point, releases the lock, and triggers a local
sanitized systemd failure hook. Health returns 0 for a point at or below six
hours, 1 when stale, and 2 for invalid or unavailable state/configuration.
External alerting is intentionally unconfigured.

Configuration is per-instance, root-controlled, outside Git, and contains an
age recipient file path but no private identity or credentials. Local staging
and off-host destinations must be distinct and validated. The disposable
rehearsal uses fictional data and an accelerated test-only driver; production
installation and recurring production RPO remain unproven until authorized
and observed.

## Consequences

The design avoids completion-time schedule drift, bounds the designed RPO
interval, supports safe catch-up after downtime, and keeps customer instances
isolated. Separate daily/monthly points make retention classification explicit.
`Persistent=true` configures one catch-up opportunity after downtime, but live
host-downtime behavior is not proven by repository CI. Operational deployment,
external alerting, and customer-specific policy remain outside this change.

The service templates use `Restart=on-failure` with a bounded restart delay and
burst limit. This allows a timer-triggered lock collision (CLI exit 3) to be
retried by systemd without treating contention as a successful backup. The
disposable Linux runtime gate in
`tools/backup/test_m29_systemd_runtime.sh` is the evidence path for validating
timer activation, persistent catch-up, and cross-tier retry; test-only timer
overrides do not alter the production cadence or jitter configuration.

## Alternatives rejected

- A completion-time loop was rejected because its schedule drifts.
- A global cron job was rejected because per-instance identity, locking, and
  status ownership would be less explicit.
- A scheduler-owned backup implementation was rejected because M29.1 already
  provides the supported archive, verification, transfer, and retention
  contracts.
