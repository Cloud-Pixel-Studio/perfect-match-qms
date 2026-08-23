# ADR-058: RC6 Lifecycle And Oliva Pilot Retirement

## Status

Accepted for `v1.0.0-rc6`.

## Decision

Perfect Match QMS uses DEV for engineering validation and the fictional Demo
for public product validation. The Oliva Torras technical pilot is retired and
must not be restarted as part of normal development or release validation.

## Retirement Controls

Before teardown, the exact Oliva database and filestore were archived to the
VM-local retirement backup directory and the archive checksum and nested
database/filestore contents were validated. Only the verified Oliva database,
containers, volumes, network, secrets, and ports were removed. Demo, DEV,
Plane, historical documentation, and Plane work-item history were preserved.

The backup contains sensitive configuration and remains outside Git, GitHub,
Plane, and release assets.

## Consequences

Current deployment instructions no longer provide Oliva startup or restore
commands. Historical Oliva docs remain available for traceability and are not
active runbooks. Commercial licensing is a future product decision and is not
implemented by this ADR.
